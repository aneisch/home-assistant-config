#!/bin/bash

# Called by sleepwatcher to tell Home Assistant when macbook inactive
# /Users/aneisch/Library/LaunchAgents/andrew.sleepwatcher-20compatibility-localuser.plist

/usr/local/bin/mosquitto_pub -h HOSTNAME -p 8883 --cafile /etc/ssl/certs/trustid-x3-root.pem -u MQTT_USER -P MQTT_PASS -t 'sensor/andrew_macbook' -m '{"active":false}'
