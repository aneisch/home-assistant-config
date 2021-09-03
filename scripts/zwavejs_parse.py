#!/usr/bin/env python3

import json

with open('/opt/homeassistant/.storage/core.device_registry') as json_file:
    data = json.load(json_file)

devices = {}

for entry in data['data']['devices']:
    #print(entry)
    if len(entry['identifiers']) > 0:
        for connection in entry['identifiers'][0]:
            #print(connection)
            if "zwave_js" in str(connection):
                #print(entry)
                device = f"{entry['manufacturer']} {entry['model']}"
                if device in devices:
                    devices[device] += 1
                else:
                    devices[device] = 1

for device,count in sorted(devices.items()):
    print(count, device)