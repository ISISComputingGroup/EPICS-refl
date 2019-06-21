@echo off
setlocal
set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%..\..\..\config_env.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255
set EPICS_CA_MAX_ARRAY_BYTES=1000000

set PYTHONUNBUFFERED=TRUE

C:\instrument\apps\python\python.exe %MYDIRBLOCK%RemoteIocServer\remote_ioc_server.py --pv_prefix %MYPVPREFIX% --ioc_names AMINT2L_01
