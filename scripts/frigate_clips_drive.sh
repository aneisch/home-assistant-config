#!/bin/bash

clip_id=$1

cd /frigate
wget -O /frigate/`date +%m_%d_%Y_%H_%M_%S.mp4` http://localhost:5000/api/events/$clip_id/clip.mp4

# Remove all but latest 120 clips
rm `ls -t /frigate | awk 'NR>120'` &> /dev/null
