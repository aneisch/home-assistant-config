#!/bin/bash

# WIP.. sort of..

camera=$1
height=$2
width=$3
file=$4

wget -O $4 http://10.0.1.22:1984/api/frame.jpeg?src=$1&h=$2&h=$3&q=60
