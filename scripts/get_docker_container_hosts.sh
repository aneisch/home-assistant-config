#!/bin/sh

# Get labels, extract Host rules, deduplicate, and join with commas
HOSTS=$(docker ps -a --format '{{.Labels}}' | \
        grep -oP 'Host\(`\K[^`]+' | \
        sort -u | \
        tr '\n' ',' | \
        sed 's/,$//')

# Output as a JSON object
echo "{\"hosts\": \"$HOSTS\"}" > /tmp/docker_hostnames.json