#!/bin/bash

# Update cloudflare firewall rule for restricted things

# API token
token="TOKEN")
# Find this on right on zone home page
zone="XXX"
# Find this from API
filter="XXX"

# Pass the old IP and new IP as args
old=$1
new=$2

expression=$(curl --silent -X GET -H "Content-Type:application/json" -H "Authorization: Bearer $token" "https://api.cloudflare.com/client/v4/zones/$zone/filters/$filter" | jq -r .result.expression | sed -e "s/$old/$new/g" ) 

expression=$(echo $expression | sed -e 's/"/\\"/g')

# Post new expression
curl -X PUT -H "Content-Type:application/json" -H "Authorization: Bearer $token" -d "{\"id\":\"$filter\", \"expression\":\"$expression\"}" "https://api.cloudflare.com/client/v4/zones/$zone/filters/$filter"
