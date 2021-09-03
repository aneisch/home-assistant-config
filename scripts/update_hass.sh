#!/bin/bash

ssh nuc 'nohup sh -c "docker-compose -f /opt/docker-compose/unified/docker-compose.yml pull --quiet homeassistant; docker-compose -f /opt/docker-compose/unified/docker-compose.yml up -d homeassistant; docker image prune -a --filter until=24h -f"'
