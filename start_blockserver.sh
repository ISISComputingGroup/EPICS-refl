#!/bin/bash

SCRIPT=$(readlink -f ${BASH_SOURCE[0]})
SCRIPTPATH=`dirname "$SCRIPT"`
MYDIRBLOCK=$SCRIPTPATH

# Ensure environment is set up
if [ -z "$EPICS_ROOT" ]; then
    . $MYDIRBLOCK/../../../config_env_base.sh
fi

. "$MYDIRBLOCK/stop_blockserver.sh"

EPICS_CAS_INTF_ADDR_LIST="127.0.0.1"
EPICS_CAS_BEACON_ADDR_LIST="127.255.255.255"

IOCLOGROOT="$ICPVARDIR/logs/ioc"

BLOCKSERVER_CONSOLEPORT="9006"

echo "Starting blockserver (console port $BLOCKSERVER_CONSOLEPORT)"
BLOCKSERVER_CMD="/bin/bash -i -O huponexit $MYDIRBLOCK/start_blockserver_cmd.sh"

# Unlike IOC we are not using "--noautorestart --wait" so gateway.py will start immediately and also automatically restart on exit

procServ --logstamp --logfile="$IOCLOGROOT/BLOCKSVR-$(date +'%Y%m%d').log" --timefmt="%c" --restrict --ignore="^D^C" --name=BLOCKSVR --pidfile="$EPICS_ROOT/EPICS_BLOCKSVR.pid" $BLOCKSERVER_CONSOLEPORT $BLOCKSERVER_CMD 

