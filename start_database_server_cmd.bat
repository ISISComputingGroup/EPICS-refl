REM @echo off

set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%..\..\..\config_env_base.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set PYTHONUNBUFFERED=TRUE

%PYTHONW% %MYDIRBLOCK%DatabaseServer\database_server.py -od %MYDIRBLOCK%..\..\..\iocstartup -f ISIS

