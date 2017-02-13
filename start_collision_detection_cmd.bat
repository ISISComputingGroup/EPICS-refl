REM @echo off

set MYDIRCD=%~dp0
call %MYDIRCD%..\..\..\config_env_base.bat

rem %HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set PYTHONUNBUFFERED=TRUE

echo on
rem %PYTHONW% %MYDIRCD%\CollisionDetection\main.py
%PYTHON% %MYDIRCD%\CollisionDetection\main.py
