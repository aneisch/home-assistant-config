#!/bin/bash

LOGFILE=/var/log/modemlog.log
MODEM=/dev/gsm_modem
INTERVAL=5
MESSAGE=$1
MESSAGE_STRING="{\"k\":\"SIM_KEY\",\"d\":\"$MESSAGE\"}"
MESSAGE_LENGTH=${#MESSAGE_STRING}

LOGDATE="date +%Y%m%dT%H%M%S"

# write command to modem
wrmodem () {
    echo -ne "$*"'\r\n' >"$MODEM"
    log "--- sent: $*"
}

# log message to a logfile
log () {
    echo "$($LOGDATE) $@" >>"$LOGFILE"
}

# logger
{
    trap 'log "=== logger stopped $BASHPID"' EXIT
    log "=== logger started: $BASHPID"
    while true ; do
        if read ; then
            log "$(tr -d \\r <<<"$REPLY")"
        fi
    done
} <"$MODEM" &

LOGGERPID=$!
trap 'kill $LOGGERPID' EXIT

    #wrmodem "AT+CMEE=2"
    #sleep 2
    wrmodem "AT+CFUN=1"
    sleep 2
    wrmodem "AT+CIPSHUT"
    sleep 5
    wrmodem 'AT+CSTT="hologram"'
    sleep 5
    wrmodem "AT+CIICR"
    sleep 5
    wrmodem "AT+CIFSR"
    sleep 5
    wrmodem "AT+CIPSTART=\"TCP\",\"cloudsocket.hologram.io\",9999"
    sleep 8
    wrmodem "AT+CIPSEND=$MESSAGE_LENGTH"
    sleep 1
    wrmodem "$MESSAGE_STRING"
    sleep 2
    wrmodem "AT+CIPSHUT"
