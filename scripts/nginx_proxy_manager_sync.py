#!/usr/bin/env python3

"""
Executed by Home Assistant via SSH
API key needs edit permissions
"""

import sqlite3
import CloudFlare

con = sqlite3.connect('/opt/nginx-proxy-manager/database.sqlite')
cur = con.cursor()
cf = CloudFlare.CloudFlare()

def add_cloudflare_record(dns_name):
    zone_id = "ZONE_ID"
    cf = CloudFlare.CloudFlare(token="TOKEN")

    dns_record = {'name': dns_name, 'type':'CNAME', 'content':'google.com', 'proxied': True}

    try:
        r = cf.zones.dns_records.post(zone_id, data=dns_record)
        print(r)
    except CloudFlare.CloudFlareAPIError as e:
        pass

for row in cur.execute('SELECT domain_names FROM proxy_host'):
        domain_names = eval(row[0])
        for name in domain_names:
            try:
                add_cloudflare_record(name.split(".")[0])
            except:
                pass
