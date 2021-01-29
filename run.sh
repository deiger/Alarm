#!/bin/bash
set -e

ARGS=
for ARG in port key login zones mqtt_discovery_max_zone serialport pima_host pima_port mqtt_host mqtt_port mqtt_client_id mqtt_topic; do
  VAL=$(jq -r ".$ARG // \"\"" $OPTIONS_FILE)
  if [ -n "$VAL" ]; then
    ARGS="$ARGS --$ARG \"$VAL\""
  fi
done
MQTT_USER=$(jq -r 'if (.mqtt_user and .mqtt_pass) then (.mqtt_user + ":" + .mqtt_pass) else "" end' $OPTIONS_FILE)
if [ -n "$MQTT_USER" ]; then
  ARGS="$ARGS --mqtt_user \"$MQTT_USER\""
fi
LOG_LEVEL=$(jq -r '.log_level | ascii_upcase // "WARNING"' $OPTIONS_FILE)

/usr/bin/python3 -u pima_server.py --log_level $LOG_LEVEL $ARGS
