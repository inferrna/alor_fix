import yaml
from typing import Any

swagga = yaml.safe_load(open("WarpOpenAPIv2.yml", "r"))

tagged_descriptions = {'Ценные бумаги / инструменты': 'securities',
 'Работа с заявками': 'orders',
 'Информация о клиенте': 'users',
 'Подписки и события (WebSocket)': 'subscriptions',
 'Другое': 'other', 
 'Стоп-заявки v2 (beta)': 'v2orders' }

all_tag_descriptions = set()
for k in swagga["paths"]:
    for kt in swagga["paths"][k]:
        if "tags" in swagga["paths"][k][kt]:
            new_tags = []
            for desc in swagga["paths"][k][kt]["tags"]:
                assert desc in tagged_descriptions, f'не найден тег для {found_desc}'
                new_tags.append(tagged_descriptions[desc])
                #all_tag_descriptions.add(desc) # Uncomment to collect all possible descriptions
            swagga["paths"][k][kt]["tags"] = new_tags
print(all_tag_descriptions)

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
def fix_enum_prop(component: dict[str, Any]):
    #print(f"Fixing {component}")
    if type(component) is list:
        for c in component:
            fix_enum_prop(c)
    if not type(component) is dict:
        return

    new_properties = component

    for k, prop in component.items():
        if not type(prop) is dict:
            continue
        if 'required' not in prop:
            prop['required'] = True

        if 'time' in k.lower() and not 'format' in prop:
            if prop['type'] == 'string':
                prop['format'] = 'date-time'
            if prop['type'] == 'integer':
                prop['format'] = 'int64'
        if (k.endswith('id') or k in ['orderno']) and not 'format' in prop and prop['type'] == 'integer':
            prop['format'] = 'int64'

        name = prop['name'] if 'name' in prop else ""
        if 'enum' in prop:
            values = prop['enum']
            #all_enums.add(tuple(values))
            found_enum = get_known_enum(values)

            if found_enum is None:
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


known_components = [(k, v) for k, v in swagga['components']['schemas'].items()]

for k, component in known_components:
    if 'properties' in component:
        fix_enum_prop(component['properties'])

for req_url, req_desc in swagga['paths'].items():
    #print(req_desc)
    for method, component in req_desc.items():
        if 'parameters' in component:
            print(f"Found props for {req_url}")
            fix_enum_prop(component['parameters'])

print(all_enums)





yaml.dump(swagga, open('fixed.yaml', 'w'))
with open('fixed.yaml', 'w', encoding='utf-8') as fp:
    yaml.dump(swagga, stream=fp, allow_unicode=True)



