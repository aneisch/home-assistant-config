#!/bin/bash


LAN=`curl -s 'http://10.0.1.2/JNAP/'   -H 'Accept: */*'   -H 'Cache-Control: no-cache'   -H 'Content-Type: application/json; charset=UTF-8'   -b 'visited-index=true; admin-auth=Basic%20YWRtaW46RmxhZ21hbi1jZXJ0YWludHktY3Jpc3B5MQ%3D%3D'   -H 'X-JNAP-Action: http://linksys.com/jnap/core/Transaction'   -H 'X-JNAP-Authorization: Basic YWRtaW46RmxhZ21hbi1jZXJ0YWludHktY3Jpc3B5MQ=='   --data-raw '[{"action":"http://linksys.com/jnap/router/GetEthernetPortConnections","request":{}}]'   --insecure | jq -r '.responses[0].output.lanPortConnections[3]'`

WAN=`curl -s 'http://10.0.1.2/JNAP/'   -H 'Accept: */*'   -H 'Cache-Control: no-cache'   -H 'Content-Type: application/json; charset=UTF-8'   -b 'visited-index=true; admin-auth=Basic%20YWRtaW46RmxhZ21hbi1jZXJ0YWludHktY3Jpc3B5MQ%3D%3D'   -H 'X-JNAP-Action: http://linksys.com/jnap/core/Transaction'   -H 'X-JNAP-Authorization: Basic YWRtaW46RmxhZ21hbi1jZXJ0YWludHktY3Jpc3B5MQ=='   --data-raw '[{"action":"http://linksys.com/jnap/router/GetEthernetPortConnections","request":{}}]'   --insecure | jq -r '.responses[0].output.wanPortConnection'`

echo $LAN
echo $WAN