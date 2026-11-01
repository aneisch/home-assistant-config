#!/bin/bash

# $1 is operation
# $2 is optional branch for switch-branch

# Commands run over SSH from inside the HA container. Anything that recreates
# the container must be fully detached on the host (output redirected, stdin
# closed, backgrounded) or it gets killed when the container (and this SSH
# session) goes away mid-run. Output lands in $LOG on the host.
COMPOSE="docker compose -f /opt/docker-compose/unified/docker-compose.yml"
LOG=/tmp/hass_operations.log

# We use $1 to look at the first word typed after the script name
case "$1" in
  "update")
    ssh -n nuc "nohup sh -c 'date; $COMPOSE pull --quiet homeassistant; sleep 5; $COMPOSE up -d homeassistant; docker image prune -a --filter until=24h -f' > $LOG 2>&1 < /dev/null &"
    ;;
  "pull")
    ssh -n nuc "nohup sh -c 'date; $COMPOSE pull --quiet homeassistant' > $LOG 2>&1 < /dev/null &"
    ;;
  "switch-branch")
    # Synchronous on purpose: "update" runs right after and must see the new tag
    branch=$2
    ssh nuc 'nohup sh -c "sed -i -e "s%ghcr.io/home-assistant/home-assistant:.*%ghcr.io/home-assistant/home-assistant:'$branch'%" /opt/docker-compose/homeassistant/docker-compose.yml && /usr/local/bin/update-compose.sh"'
    ;;
  *)
    echo "Error: Invalid command '$1'"
    exit 1
    ;;
esac