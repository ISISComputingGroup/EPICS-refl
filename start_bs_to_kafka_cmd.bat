REM @echo off

set MYDIRCD=%~dp0
call %MYDIRCD%..\..\..\config_env_base.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set PYTHONUNBUFFERED=TRUE

if "%ISIS_INSTRUMENT%" == "1" (
    set BROKER=livedata.isis.cclrc.ac.uk
) else (
    REM point at the test server
    set BROKER=tenten.isis.cclrc.ac.uk
)

%PYTHON% %MYDIRCD%\BlockServerToKafka\main.py -d %INSTRUMENT%_sampleEnv -c forwarder_config -b %BROKER%:9092 -p %MYPVPREFIX%
