#!/bin/bash

# Run on NUC via SSH

cd /opt/frigate

git add config.yml
git commit -m 'Autocommit by Home Assistant on change'
git push
