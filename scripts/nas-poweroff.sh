#!/bin/bash

docker stop plex
sleep 10
sudo umount -fl /plex
timeout 30 ssh -i /home/aneisch/.ssh/id_rsa root@10.0.1.20 '/frontview/bin/autopoweroff 2&> /dev/null; exit'