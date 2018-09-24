REM @echo off
setlocal
set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%stop_blockserver.bat
set CYGWIN=nodosfilewarning
call %MYDIRBLOCK%..\..\..\config_env_base.bat

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set IOCLOGROOT=%ICPVARDIR%/logs/ioc
for /F "usebackq" %%I in (`cygpath %IOCLOGROOT%`) do SET IOCCYGLOGROOT=%%I

set BLOCKSERVER_CONSOLEPORT=9006

@echo Starting blockserver (console port %BLOCKSERVER_CONSOLEPORT%)
set BLOCKSERVER_CMD=%MYDIRBLOCK%start_blockserver_cmd.bat

REM Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

%ICPTOOLS%\cygwin_bin\procServ.exe --logstamp --logfile="%IOCCYGLOGROOT%/BLOCKSVR-%%Y%%m%%d.log" --timefmt="%%c" --restrict --ignore="^D^C" --name=BLOCKSVR --pidfile="/cygdrive/c/windows/temp/EPICS_BLOCKSVR.pid" %BLOCKSERVER_CONSOLEPORT% %BLOCKSERVER_CMD% 
