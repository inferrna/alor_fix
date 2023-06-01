import yaml

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
    "Exchange": ['MOEX', 'SPBX'],
    "OrderStatus": ['working', 'filled', 'canceled', 'rejected'],
    "OrderType": ['limit', 'market'],
    "StopOrderType": ['stop', 'stoplimit'],
    "Duration": [15, 60, 300, 3600, 'D', 'W', 'M', 'Y']
}

for known_enum, known_enum_values in known_enums.items():
    swagga['components']['schemas'][known_enum] = {'type': 'string', 'enum': known_enum_values}

def get_known_enum(values: list[str]) -> str|None:
    for enum_name, enum_values in known_enums.items():
        is_this_enum = True
        for v in values:
            is_this_enum &= v in enum_values
        if is_this_enum:
            return enum_name
    return None

for k, component in swagga['components']['schemas'].items():
    if 'properties' in component:
        new_properties = component['properties']
        for k, prop in component['properties'].items():
            print(prop)
            if 'enum' in prop:
                values = prop['enum']
                #all_enums.add(tuple(values))
                known_enum = get_known_enum(values)
                if known_enum:
                    new_properties[k] = {'$ref': f'#/components/schemas/{known_enum}'}
        component['properties'] = new_properties

print(all_enums)





yaml.dump(swagga, open('fixed.yaml', 'w'))
with open('fixed.yaml', 'w', encoding='utf-8') as fp:
    yaml.dump(swagga, stream=fp, allow_unicode=True)



