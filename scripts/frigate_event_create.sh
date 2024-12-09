#!/bin/bash

camera=$1
label=$2

curl --silent -X POST -H 'Content-Type: application/json' --data '{ "duration": 30, "include_recording": true }' http://localhost:5000/api/events/$camera/$label/create
