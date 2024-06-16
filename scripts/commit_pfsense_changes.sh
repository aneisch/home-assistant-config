#!/bin/bash

# Run on NUC via SSH
cd /opt/pfsense

scp -P 23 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no backup@10.0.1.1:/cf/conf/config.xml /opt/pfsense/

git add config.xml
git commit -m 'Autocommit by Home Assistant'
git push