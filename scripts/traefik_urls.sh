#!/bin/bash

# Read active routers from Traefik API and output JSON of all host rules

IFS=, read -d '' -a myarray <<< $(curl --silent https://traefik.home.mydomain.com/api/http/routers | jq -r . | grep -i rule | grep -v "HostRegexp" | sed -e 's/.*ost(`//' -e 's/`.*//')

json_array=$(jq --compact-output --null-input '$ARGS.positional' --args -- ${myarray[@]})
echo "{\"urls\": $json_array }"
