#!/usr/bin/env python

# Read hacs repo file find what is installed 
# by HACS so it can be populated in README

import json

types = {}

with open("/opt/homeassistant/.storage/hacs.repositories") as fp:
    content = json.load(fp)

for item in content["data"]:
    if content["data"][item]["installed"] == True:
        name = content["data"][item]["full_name"].encode("ascii")
        type = content["data"][item]["category"]
        string = name.encode("ascii")
        if type not in types:
            types[type] = [string]
        else:
            types[type].append(string)

for type, entries in types.items():
    print("**{}**:<br>".format(type.title()))
    for package in sorted(entries):
        print("[{}](https://github.com/{})<br>".format(package, package))
    print
