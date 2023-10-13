#!/bin/bash

camera=$1

cat /config/timelapse/camera.$camera/*.jpg | ffmpeg -f image2pipe -r 8 -vcodec mjpeg -y -i - -vcodec libx264 /config/timelapse/$camera.mp4
