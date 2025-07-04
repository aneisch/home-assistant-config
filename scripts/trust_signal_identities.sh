#!/bin/bash

SIGNAL_USER="signal_number"

# Get list of identities
IDENTITIES=$(curl -s "127.0.0.1:8800/v1/identities/${SIGNAL_USER}")

echo "$IDENTITIES" | jq -c '.[] | select(.status == "UNTRUSTED")' | while read -r identity; do
  NUMBER=$(echo "$identity" | jq -r '.number')
  echo "Trusting identity: $NUMBER"
  curl -s -X PUT "${BASE_URL}/v1/identities/${SIGNAL_USER}/trust/${NUMBER}" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{"trust_all_known_keys": true}'
done