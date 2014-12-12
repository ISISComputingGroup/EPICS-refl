REM @echo off

set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%..\..\config_env_base.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set MYDIRGATE=%MYDIRBLOCK%..\..\..\gateway
if exist "%ICPSETTINGSDIR%/gwblock.pvlist" (
    set GWBLOCK_PVLIST=%ICPSETTINGSDIR%/gwblock.pvlist
) else (
    set GWBLOCK_PVLIST=%MYDIRGATE%\gwblock_dummy.pvlist
) 

%PYTHONW% %MYDIRBLOCK%BlockServer\block_server.py -od %MYDIRBLOCK%..\..\iocstartup -cd %ICPCONFIGROOT% -pv %GWBLOCK_PVLIST%
