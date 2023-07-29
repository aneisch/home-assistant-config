#!/bin/bash

clip_id=$1

cd /frigate
wget -O /frigate/`date +%m_%d_%Y_%H_%M_%S_1690389398.964135-kk1s6p.mp4` http://10.0.1.22:5000/api/events/$clip_id/clip.mp4

# Remove all but latest 60 clips
rm `ls -t /frigate | awk 'NR>60'` &> /dev/null
