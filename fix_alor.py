import yaml
from typing import Any
import json
import sys
#from collections import OrderedDict

filename_in = sys.argv[1]
filename_out = f"fixed_{filename_in}"

swagga = yaml.safe_load(open(filename_in, "r"))

tagged_descriptions = {
 'Ценные бумаги / инструменты': 'securities',
 'Instruments': 'securities',
 'Работа с заявками': 'orders',
 'Orders': 'orders',
 'OrdersWebSocket': 'ws_orders',   
 'Authorization': 'auth',
 'OrderGroups': 'ws_orders',   
 'OrdersWebSocket': 'order_groups',   
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
    if name not in swagga['components']['schemas']:
        swagga['components']['schemas'][name] = {'type': 'string', 'enum': values}
    else:
        allvals = set(swagga['components']['schemas'][name]['enum'] + values)
        swagga['components']['schemas'][name]['enum'] = list(allvals)

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

    if schema_is_int64(component):
        fix_schema_int64(component)

    new_properties = component

    if 'schema' in new_properties and 'name' in new_properties:
        prop = new_properties['schema']
        if field_is_int64(new_properties['name']) and not 'format' in prop and 'type' in prop and prop['type'] == 'integer':
            new_properties['schema']['format'] = 'int64'

        

    for k, prop in new_properties.items():
        if not type(prop) is dict:
            continue
        fix_enum_prop(prop)
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
                print(f"Enum {found_enum} was found for {k}")
                new_properties[k] = {'$ref': f'#/components/schemas/{found_enum}'}
        elif k in exnames or name in exnames:
            print("Exchange enum was forced")
            new_properties[k] = {'$ref': f'#/components/schemas/Exchange'}
        elif k in fmnames or name in fmnames:
            print("Format enum was forced")
            new_properties[k] = {'$ref': f'#/components/schemas/JsonFormat'}
        component[k] = new_properties[k]
    for k, v in new_properties.items():
        component[k] = v

def get_dict_path(obj: dict[Any, Any], keys: list[Any]) -> Any:
    current_val = obj
    for key in keys:
        current_val = current_val[key]
    return current_val

var_properties = ['required', 'in','nullable', 'name']

def transfer_keys_values(source: dict[str, Any], dest: dict[str, Any], keys: list[str]):
    for key in keys:
        if key in source:
            dest[key] = source[key]

def fix_unnamed_refs(component: list[Any]|dict[str, Any], swagga_original: dict[str, Any], objects_to_clean: set[str]):
    if type(component) is dict:
        for k, v in component.items():
            #print(f"Proceed: -----{k}------------")
            fix_unnamed_refs(v, swagga_original, objects_to_clean)

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
            objects_to_clean.add(raw_ref_path)
            ref_object = get_dict_path(swagga_original, ref_path)
            if not 'name' in ref_object:
                print("WARNING: unnamed pure ref found")
                continue
            new_c = {}
            transfer_keys_values(ref_object, new_c, var_properties)
            new_c['schema'] = {'$ref': c['$ref']}
            indexes2replace.append(i)
            new_component.append(new_c)
            #new_component[ref_object['name']] = new_c
            if 'schema' in ref_object:
                for key in ref_object['schema']:
                    ref_object[key] = ref_object['schema'][key]
                ref_object.pop('schema')
            print(f"Found pure ref: {raw_ref_path} -> {ref_path}: {ref_object}")
        else:
            fix_unnamed_refs(c, swagga_original, objects_to_clean)

    for i,c in enumerate(indexes2replace):
        component[c] = new_component[i]


def remove_all_keys(data: dict[str, Any]|list[Any], keys2rm: list[str]):
    if type(data) is dict:
        for k in keys2rm:
            if k in data:
                data.pop(k)
        for k, v in data.items():
            remove_all_keys(v, keys2rm)
    if type(data) is list:
        for v in data:
            remove_all_keys(v, keys2rm)


def compare_types(type_x: dict[str, Any], type_y: dict[str, Any]) -> bool:
    if not type(type_x) is dict or not type(type_y) is dict:
        return False
    if 'type' in type_x and 'type' in type_y:
        is_similar = type_x['type'] == type_y['type']
        is_object = (type_x['type'] == 'object') and (type_y['type'] == 'object')
        is_array = (type_x['type'] == 'array') and (type_y['type'] == 'array')
    else:
        is_similar, is_object, is_array = False, False, False
    k = 'format'
    both_has_same_k = (k in type_x) == (k in type_y)
    is_similar = is_similar and both_has_same_k
    if is_similar and k in type_x and k in type_y:
        is_similar = is_similar and type_x[k] == type_y[k]
    k = 'enum'
    is_similar = is_similar and (k in type_x) == (k in type_y)
    if is_similar and k in type_x and k in type_y:
        print("Mostly similar, compare enum values..")
        vals_x = set(type_x[k])
        vals_y = set(type_y[k])
        is_similar = is_similar and (vals_x.issubset(vals_y) or vals_y.issubset(vals_x))
    if is_object and is_similar:
        tx = json.loads(json.dumps(type_x))
        ty = json.loads(json.dumps(type_y))
        remove_all_keys(tx, ["description", "example"])
        remove_all_keys(ty, ["description", "example"])
        is_similar = is_similar and tx == ty
    if is_array and is_similar:
        is_similar = type_x['items']['$ref'] == type_y['items']['$ref']
    return is_similar




def join_same_types(types: dict[str, dict[str, Any]]) -> dict[tuple[str,str], list[tuple[str,str]]]:
    fixed_keys = []
    replacements: dict[tuple[str,str], list[tuple[str,str]]] = {}
    two_lvl_keys = [(ka, kb) for ka in types.keys() for kb in types[ka].keys()]

    #print(two_lvl_keys)
    for key_a in two_lvl_keys:
        if key_a in fixed_keys:
            continue
        similar_types: list[tuple[str,str]] = [key_a]
        type_a = types[key_a[0]][key_a[1]]
        for key_b in two_lvl_keys:
            if key_b in fixed_keys or key_b in similar_types:
                continue
            type_b = types[key_b[0]][key_b[1]]
            if compare_types(type_a, type_b):
                print(f"Type {key_a} is similar to {key_b}")
                fixed_keys.append(key_b)
                similar_types.append(key_b)
        if len(similar_types)>1:
            similar_types.sort(key = lambda x: len(x[1]))
            is_enum = 'enum' in type_a
            if is_enum:
                similar_types.sort(key = lambda x: (-len(types[x[0]][x[1]]['enum']), len(x[1])))
            best_type_name = similar_types.pop(0)
            replacements[best_type_name] = similar_types
    return replacements

        

# Фиксим enum
known_components = [(k, v) for k, v in swagga['components']['schemas'].items()]
for k, component in known_components:
    for k in ['properties' , 'allOf']:
        if k in component:
            fix_enum_prop(component[k])
            

for req_url, req_desc in swagga['paths'].items():
    #print(req_desc)
    for method, component in req_desc.items():
        if 'parameters' in component:
            print(f"Found params for {req_url}")
            fix_enum_prop(component['parameters'])




print(all_enums)

o2cl = set()
fix_unnamed_refs(swagga, swagga, o2cl)

## Убираем лишние свойства у типов
for raw_ref_path in o2cl:
    ref_path = raw_ref_path.replace("#/", "").split("/")
    ref_object: dict[str, Any] = get_dict_path(swagga, ref_path)
    for prop in var_properties:
        if prop in ref_object:
            ref_object.pop(prop)

def is_primitive_type(tp: dict[str, str])->bool:
    is_prim = 'type' in tp and tp['type'] in ['string', 'number', 'integer', 'float', 'boolean']
    return is_prim and not 'enum' in tp

def fix_refs_to_primitive(data: dict[str, Any]|list[Any], swagga: dict[str, Any], doomed_types: list[str]):
    if type(data) is dict:
        pairs = [(k, v) for k, v in data.items() if k == "$ref" and type(v) is str]
        if len(pairs)>0:
            r, raw_ref_path = pairs[0]
            ref_path = raw_ref_path.replace("#/", "").split("/")
            tp = get_dict_path(swagga, ref_path)
            if is_primitive_type(tp):
                if raw_ref_path not in doomed_types:
                    print(f"Replace {raw_ref_path} with primitive {tp['type']}")
                    doomed_types.append(raw_ref_path)
                data.pop(r)
                for k, v in tp.items():
                    data[k] = v
        for k, v in data.items():
            fix_refs_to_primitive(v, swagga, doomed_types)

    if type(data) is list:
        for v in data:
            fix_refs_to_primitive(v, swagga, doomed_types)

def remove_primitives(swagga):
# Заменяем рефы на алиасы примитивных типов прямой деклрацией
    refs2delete = []
    fix_refs_to_primitive(swagga, swagga, refs2delete)

#print(set(refs2delete))

# Удаляем алиасы примитивных типов
    for raw_ref in set(refs2delete):
        ref_path = raw_ref.replace("#/", "").split("/")
        v = swagga
        for key in ref_path[:-1]:
            v = v[key]
        last_k = ref_path[-1]
        if last_k == "Take":
            print(raw_ref)
            print(v)
        #if last_k in v:
            #v.pop(last_k)

remove_primitives(swagga)
remove_primitives(swagga)

def replace_type_ref(refs2replace: dict[str,str], data: dict[str, Any]|list[Any]):
    if type(data) is dict:
        pairs = [(k, v) for k, v in data.items() if k == "$ref" and type(v) is str and v in refs2replace]
        if len(pairs)>0:
            k, v = pairs[0]
            repacement = refs2replace[v]
            print(f"Replace {v} with {repacement}")
            data[k] = repacement
        for k, v in data.items():
            replace_type_ref(refs2replace, v)

    if type(data) is list:
        for v in data:
            replace_type_ref(refs2replace, v)

for root in ['components']:
# Находим одинаковые типы
    repls = join_same_types(swagga[root])

# Удаляем лишние типы
    for (ra, ka,), victims in repls.items():
        for (rb, kb,) in victims:
            if kb in swagga[root][rb]:
                swagga[root][rb].pop(kb)

# Создаём плоскую мапу соответствия старых ref новым
    flat_repls = {f"#/{root}/{rb}/{kb}":f"#/{root}/{ra}/{ka}" for ra, ka in repls.keys() for rb, kb in repls[(ra, ka,)]}

# Заменяем типы по мапе
    replace_type_ref(flat_repls, swagga)

def fix_components(data: dict[str, Any]):
    if type(data) is dict:
        if 'allOf' in data and len([k for r in data['allOf'] for k in r.keys() if k=='$ref'])==0:
            d = data.pop('allOf')
            if type(d) is dict:
                data.update(d)
            else:
                for dd in d:
                    data.update(dd)
            print(f"oneOf became: {data}")
        if 'oneOf' in data:
            v = [v for r in data.pop('oneOf') for v in r.values() if not 'simple' in v and not 'heavy' in v]
            data['$ref'] = v[0]
            print(f"oneOf became: {data}")
        if '$ref' in data:
            data['$ref'] = data['$ref'].replace("/parameters/", "/schemas/")
        if 'lotsize' in data and type(data['lotsize']) is dict:
            data['lotsize']['type'] = 'number'
            data['lotsize']['format'] = 'float'
        if 'enum' in data:
            if not 'type' in data:
                data['type'] = 'string'
            elif data['type'] != 'string':
                data.pop('enum')
        keys = list(data.keys())
        for k in keys:
            if 'slim' in k or 'heavy' in k or k=='examples':
                data.pop(k)
        for k, v in data.items():
            fix_components(v)
    if type(data) is list:
        for v in data:
            fix_components(v)


# Уносим модели из parameters
fix_components(swagga)

for k, v in swagga['components']['parameters'].items():
    swagga['components']['schemas'][k] = v

swagga['components'].pop('parameters')

remove_primitives(swagga)

with open('fixed.yaml', 'w', encoding='utf-8') as fp:
    yaml.dump(swagga, stream=fp, allow_unicode=True)



