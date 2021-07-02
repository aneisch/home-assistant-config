#!/bin/bash

branch=$1

ssh nuc 'nohup sh -c "sed -i -e "s%ghcr.io/home-assistant/home-assistant:.*%ghcr.io/home-assistant/home-assistant:'$branch'%" /opt/docker-compose/homeassistant/docker-compose.yml && /usr/local/bin/update-compose.sh && docker-compose -f /opt/docker-compose/unified/docker-compose.yml pull homeassistant && docker-compose -f /opt/docker-compose/unified/docker-compose.yml up -d homeassistant"'
