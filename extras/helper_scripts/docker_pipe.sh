#! /usr/bin/env bash

# To create: mkfifo /home/aneisch/.docker_pipe
# Anything sent to this pipe will be run as root...

pipe=/home/aneisch/.docker_pipe
[ -p "$pipe" ] || mkfifo -m 0600 "$pipe" || exit 1
while :; do
    while read -r cmd; do
        if [ "$cmd" ]; then
            echo "running $cmd"
            bash -c "$cmd"
        fi
    done <"$pipe"
done
