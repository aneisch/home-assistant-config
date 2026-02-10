#!/bin/bash

# $1 is operation
# $2 is optional branch for switch-branch

# We use $1 to look at the first word typed after the script name
case "$1" in
  "update")
    ssh nuc 'nohup sh -c "docker-compose -f /opt/docker-compose/unified/docker-compose.yml pull --quiet homeassistant; sleep 5; docker-compose -f /opt/docker-compose/unified/docker-compose.yml up -d homeassistant; docker image prune -a --filter until=24h -f"'
    ;;
  "pull")
    ssh nuc 'nohup sh -c "docker-compose -f /opt/docker-compose/unified/docker-compose.yml pull --quiet homeassistant"'
    ;;
  "switch-branch")
    branch=$2
    ssh nuc 'nohup sh -c "sed -i -e "s%ghcr.io/home-assistant/home-assistant:.*%ghcr.io/home-assistant/home-assistant:'$branch'%" /opt/docker-compose/homeassistant/docker-compose.yml && /usr/local/bin/update-compose.sh"'
    ;;
  *)
    echo "Error: Invalid command '$1'"
    exit 1
    ;;
esac