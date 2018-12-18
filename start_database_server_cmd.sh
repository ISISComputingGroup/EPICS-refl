#!/bin/bash

SCRIPT=$(readlink -f ${BASH_SOURCE[0]})
SCRIPTPATH=`dirname "$SCRIPT"`
export MYDIRBLOCK=$SCRIPTPATH

# Ensure environment is set up
if [ -z "$EPICS_ROOT" ]; then
    . $MYDIRBLOCK/../../../config_env_base.sh
fi

export EPICS_CAS_INTF_ADDR_LIST="127.0.0.1"
export EPICS_CAS_BEACON_ADDR_LIST="127.255.255.255"

export PYTHONUNBUFFERED="TRUE"

python "$MYDIRBLOCK/DatabaseServer/database_server.py" -od "$MYDIRBLOCK/../../../iocstartup"

