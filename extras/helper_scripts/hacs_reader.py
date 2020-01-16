#!/usr/bin/env python

# Find what is installed by HACS for README

import json

with open("/home/aneisch/homeassistant/.storage/hacs.repositories") as fp:
    content = json.load(fp)

for item in content["data"]:
    if content["data"][item]["installed"] == True:
        name = content["data"][item]["full_name"]
        print "{}(https://github.com/{})".format(name, name)
