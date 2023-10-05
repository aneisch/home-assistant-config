#!/bin/bash

cd /opt/frigate

git add config.yml
git commit -m 'Autocommit by Home Assistant on change'
git push
