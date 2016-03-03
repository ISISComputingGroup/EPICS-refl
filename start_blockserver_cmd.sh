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

export MYDIRGATE="$MYDIRBLOCK/../../../gateway"
if [ -r "$ICPSETTINGSDIR/gwblock.pvlist" ]; then
    GWBLOCK_PVLIST="$ICPSETTINGSDIR/gwblock.pvlist"
else
    GWBLOCK_PVLIST="$MYDIRGATE/gwblock_dummy.pvlist"
fi

export MYDIRVC="$MYDIRBLOCK/../../ConfigVersionControl/master"

python "$MYDIRBLOCK/BlockServer/block_server.py" -od "$MYDIRBLOCK/../../../iocstartup" -sd "$MYDIRBLOCK/../../../schema/configurations" -cd "$ICPCONFIGROOT" -pv "$GWBLOCK_PVLIST" -f ISIS

