#!/bin/bash

SCRIPT=$(readlink -f ${BASH_SOURCE[0]})
SCRIPTPATH=`dirname "$SCRIPT"`
MYDIRBLOCK=$SCRIPTPATH

# Ensure environment is set up
if [ -z "$EPICS_ROOT" ]; then
    . $MYDIRBLOCK/../../../config_env_base.sh
fi

. "$MYDIRBLOCK/stop_json_bourne.sh"

EPICS_CAS_INTF_ADDR_LIST="127.0.0.1"
EPICS_CAS_BEACON_ADDR_LIST="127.255.255.255"

IOCLOGROOT="$ICPVARDIR/logs/ioc"

JSON_BOURNE_CONSOLEPORT="9012"

echo "Starting JSON bourne (console port $JSON_BOURNE_CONSOLEPORT)"
JSON_BOURNE_CMD="/bin/bash -i -O huponexit $MYDIRBLOCK/start_json_bourne_cmd.sh

# Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

procServ --logstamp --logfile="$IOCLOGROOT/JSONBOURNE-$(date +'%Y%m%d').log" --timefmt="%c" --restrict --ignore="^D^C" --name=JSONBOURNE --pidfile="$EPICS_ROOT/EPICS_JSONBOURNE.pid" $JSON_BOURNE_CONSOLEPORT $JSON_BOURNE_CMD 

