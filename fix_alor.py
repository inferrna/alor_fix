import yaml
from typing import Any

swagga = yaml.safe_load(open("WarpOpenAPIv2.yml", "r"))

tagged_descriptions = {
 'Ценные бумаги / инструменты': 'securities',
 'Instruments': 'securities',
 'Работа с заявками': 'orders',
 'Orders': 'orders',
 'Информация о клиенте': 'users',
 'ClientInfo': 'users',
 'Подписки и события (WebSocket)': 'subscriptions',
 'Subscriptions': 'subscriptions',
 'Deprecated': 'Deprecated', 
 'Другое': 'other', 
 'Other': 'other', 
 'Стоп-заявки v2 (beta)': 'v2orders',
 'StopOrdersV2': 'v2orders',
 'Стоп-заявки v2': 'v2orders' }

all_tag_descriptions = set()
for k in swagga["paths"]:
    for kt in swagga["paths"][k]:
        if "tags" in swagga["paths"][k][kt]:
            new_tags = []
            for desc in swagga["paths"][k][kt]["tags"]:
                assert desc in tagged_descriptions, f'не найден тег для {desc}'
                new_tags.append(tagged_descriptions[desc])
                #all_tag_descriptions.add(desc) # Uncomment to collect all possible descriptions
            swagga["paths"][k][kt]["tags"] = new_tags
print(all_tag_descriptions)


def find_short_description(dt: dict[str, Any], path: str):
    if not type(dt) is dict:
        return True

    do_report = 'type' in dt and not dt['type'] in ['array', 'object']
    for k, v in dt.items():
        do_report &= find_short_description(v, path+"->"+k)

    if do_report:
        if 'description' not in dt:
            print(f'Нет описания для {path}')
        elif type(dt['description']) is str and len(dt['description'])<2:
            print(f'Пустое описание для {path}')
    return False

find_short_description(swagga, "root")

tags = []
for desc, tag in tagged_descriptions.items():
    tags.append({'name': tag, 'description': desc})

swagga['tags'] = tags


all_enums = set()
known_enums = {
    "LifePolicy": ['OneDay', 'ImmediateOrCancel', 'FillOrKill', 'AtTheClose', 'GoodTillCancelled'],
    "Operation": ['buy', 'sell'],
    "JsonFormat": ['Simple'],
    "Exchange": ['MOEX', 'SPBX'],
    "OrderStatus": ['working', 'filled', 'canceled', 'rejected'],
    "OrderType": ['limit', 'market'],
    "StopOrderType": ['stop', 'stoplimit'],
    "Duration": [15, 60, 300, 3600, 'D', 'W', 'M', 'Y']
}

for known_enum, known_enum_values in known_enums.items():
    swagga['components']['schemas'][known_enum] = {'type': 'string', 'enum': known_enum_values}


def add_new_enum(name: str, values: list[str]):
    swagga['components']['schemas'][name] = {'type': 'string', 'enum': values}

def get_known_enum(values: list[str]) -> str|None:
    for enum_name, enum_data in swagga['components']['schemas'].items():
        if not type(enum_data) is dict:
            continue
        if not 'enum' in enum_data:
            continue
        is_this_enum = True
        for v in values:
            is_this_enum &= v in enum_data['enum']
        if is_this_enum:
            return enum_name
    return None


exnames = ["exchange", "Exchange"]
fmnames = ["format", "Format"]



def has_key_value(schm: dict, key: str, vals: list[str]) -> bool:
    return (key in schm and schm[key] in vals) or (has_key_value(schm['schema'], key, vals) if 'schema' in schm else False)

def field_is_int64(field_name: str) -> bool:
    return (field_name.lower().endswith('id') or field_name in ['orderno', 'from', 'to', 'prev', 'next', 'volume'])

def schema_is_int64(schm: dict) -> bool:
    return ('description' in schm and 'UTC' in schm['description'] and has_key_value(schm, 'type', ['integer', 'number'])) or (has_key_value(schm, 'type', ['string']) and has_key_value(schm, 'format', ['integer']))

def fix_schema_int64(schm: dict):
    if 'type' in schm:
        print(f'Fixing {schm}')
        schm['type'] = 'integer'
        schm['format'] = 'int64'
    elif 'schema' in schm:
        print(f'2nd fixing {schm}')
        fix_schema_int64(schm['schema'])

def fix_enum_prop(component: dict[str, Any]):
    #print(f"Fixing {component}")
    if type(component) is list:
        for c in component:
            fix_enum_prop(c)
    if not type(component) is dict:
        return

    new_properties = component

    if 'schema' in new_properties and 'name' in new_properties:
        prop = new_properties['schema']
        if field_is_int64(new_properties['name']) and not 'format' in prop and prop['type'] == 'integer':
            new_properties['schema']['format'] = 'int64'



    if schema_is_int64(component):
        fix_schema_int64(component)
        

    for k, prop in new_properties.items():
        if not type(prop) is dict:
            continue
        if 'format' in prop and prop['format'] == 'decimal':
            prop['format'] = 'float'
        if 'required' not in prop and 'nullable' not in prop:
            if 'example' in prop and prop['example'] == None:
                prop['nullable'] = True
            else:
                prop['required'] = True

        if 'time' in k.lower() and not 'format' in prop and 'type' in prop:
            if prop['type'] == 'string':
                prop['format'] = 'date-time'
            if prop['type'] == 'integer':
                prop['format'] = 'int64'
        if field_is_int64(k) and not 'format' in prop and has_key_value(prop, 'type', ['integer']):
            fix_schema_int64(prop)

        name = prop['name'] if 'name' in prop else ""
        is_bool = 'type' in prop and prop['type'] == 'boolean'
        if 'enum' in prop and not is_bool:
            values = prop['enum']
            #all_enums.add(tuple(values))
            found_enum = get_known_enum(values)

            if found_enum is None:
                if set(values) == {"true", "false"}:
                    new_properties[k]['type'] = "boolean"
                    new_properties[k].pop('enum')
                else:
                    found_enum = k.capitalize()+"Enum"
                    add_new_enum(found_enum, values)

            if found_enum is not None:
                print("Enum was found")
                new_properties[k] = {'$ref': f'#/components/schemas/{found_enum}'}
        elif k in exnames or name in exnames:
            print("Exchange enum was forced")
            new_properties[k] = {'$ref': f'#/components/schemas/Exchange'}
        elif k in fmnames or name in fmnames:
            print("Format enum was forced")
            new_properties[k] = {'$ref': f'#/components/schemas/JsonFormat'}
        for ks in prop:
            fix_enum_prop(prop[ks])
    for k, v in new_properties.items():
        component[k] = v

def get_dict_path(obj: dict[Any, Any], keys: list[Any]) -> Any:
    current_val = obj
    for key in keys:
        current_val = current_val[key]
    return current_val

def transfer_keys_values(source: dict[str, Any], dest: dict[str, Any], keys: list[str]):
    for key in keys:
        if key in source:
            dest[key] = source[key]

def fix_unnamed_refs(component: list[Any]|dict[str, Any], swagga_original: dict[str, Any]):
    if type(component) is dict:
        for k, v in component.items():
            #print(f"Proceed: -----{k}------------")
            fix_unnamed_refs(v, swagga_original)

    if not type(component) is list:
        return
    new_component = []
    indexes2replace = []
    for i,c in enumerate(component):
        if not type(c) is dict:
            continue
        if '$ref' in c and not 'name' in c:
            raw_ref_path = c['$ref']
            ref_path = raw_ref_path.replace("#/", "").split("/")
            ref_object = get_dict_path(swagga_original, ref_path)
            if not 'name' in ref_object:
                print("WARNING: unnamed pure ref found")
                continue
            new_c = {}
            transfer_keys_values(ref_object, new_c, ['required', 'in','nullable', 'name'])
            new_c['schema'] = {'$ref': c['$ref']}
            indexes2replace.append(i)
            new_component.append(new_c)
            #new_component[ref_object['name']] = new_c
            if 'schema' in ref_object:
                for key in ref_object['schema']:
                    ref_object[key] = ref_object['schema'][key]
                ref_object.pop('schema')
            if 'enum' in ref_object and not 'type' in ref_object:
                ref_object['type'] = 'string'
            print(f"Found pure ref: {raw_ref_path} -> {ref_path}: {ref_object}")
        else:
            fix_unnamed_refs(c, swagga_original)

    for i,c in enumerate(indexes2replace):
        component[c] = new_component[i]


known_components = [(k, v) for k, v in swagga['components']['schemas'].items()]
for k, component in known_components:
    if 'properties' in component:
        fix_enum_prop(component['properties'])

for req_url, req_desc in swagga['paths'].items():
    #print(req_desc)
    for method, component in req_desc.items():
        if 'parameters' in component:
            print(f"Found params for {req_url}")
            fix_enum_prop(component['parameters'])

print(all_enums)

fix_unnamed_refs(swagga, swagga)




yaml.dump(swagga, open('fixed.yaml', 'w'))
with open('fixed.yaml', 'w', encoding='utf-8') as fp:
    yaml.dump(swagga, stream=fp, allow_unicode=True)



