#!/usr/bin/env python

# Read hacs repo file Find what is installed 
# by HACS so it can be populated in README

import json

types = {}

with open("/home/aneisch/homeassistant/.storage/hacs.repositories") as fp:
    content = json.load(fp)

for item in content["data"]:
    if content["data"][item]["installed"] == True:
        name = content["data"][item]["full_name"]
        type = content["data"][item]["category"]
        string = "[{}](https://github.com/{})<br>".format(name, name)
        if type not in types:
            types[type] = [string]
        else:
            types[type].append(string)

for type, entries in types.items():
    print("### {}".format(type.title()))
    for package in entries:
        print(package)
    print
        
