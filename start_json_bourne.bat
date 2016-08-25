REM @echo off

set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%stop_json_bourne.bat
set CYGWIN=nodosfilewarning
call %MYDIRBLOCK%..\..\..\config_env_base.bat

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set IOCLOGROOT=%ICPVARDIR%/logs/ioc
for /F "usebackq" %%I in (`cygpath %IOCLOGROOT%`) do SET IOCCYGLOGROOT=%%I

set JSON_BOURNE_CONSOLEPORT=9012

@echo Starting JSON bourne (console port %JSON_BOURNE_CONSOLEPORT%)
set JSON_BOURNE_CMD=%MYDIRBLOCK%start_json_bourne_cmd.bat

REM Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

%ICPTOOLS%\cygwin_bin\procServ.exe --logstamp --logfile="%IOCCYGLOGROOT%/JSONBOURNE-%%Y%%m%%d.log" --timefmt="%%c" --restrict --ignore="^D^C" --name=JSONBOURNE --pidfile="/cygdrive/c/windows/temp/EPICS_JSONBOURNE.pid" %JSON_BOURNE_CONSOLEPORT% %JSON_BOURNE_CMD% 
