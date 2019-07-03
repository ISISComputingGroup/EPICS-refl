#!/bin/bash

SCRIPT=$(readlink -f ${BASH_SOURCE[0]})
SCRIPTPATH=`dirname "$SCRIPT"`
MYDIRBLOCK="$SCRIPTPATH"

# Ensure environment is set up
if [ -z "$EPICS_ROOT" ]; then
    . "$MYDIRBLOCK/../../../config_env_base.sh"
fi

. "$MYDIRBLOCK/stop_database_server.sh"

EPICS_CAS_INTF_ADDR_LIST="127.0.0.1"
EPICS_CAS_BEACON_ADDR_LIST="127.255.255.255"

IOCLOGROOT="$ICPVARDIR/logs/ioc"

DBSERVER_CONSOLEPORT="9009"

echo "Starting dbserver (console port $DBSERVER_CONSOLEPORT)"
DBSERVER_CMD="/bin/bash -i -O huponexit $MYDIRBLOCK/start_database_server_cmd.sh"

# Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

procServ --logstamp --logfile="$IOCLOGROOT/DBSVR-$(date +'%Y%m%d').log" --timefmt="%c" --restrict --ignore="^D^C" --name=DBSVR --pidfile="$EPICS_ROOT/EPICS_DBSVR.pid" $DBSERVER_CONSOLEPORT $DBSERVER_CMD 

