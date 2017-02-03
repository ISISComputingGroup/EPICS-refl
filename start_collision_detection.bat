REM @echo off

set MYDIRCDSVR=%~dp0
call %MYDIRCDSVR%stop_collision_detection.bat
set CYGWIN=nodosfilewarning
call %MYDIRCDSVR%..\..\..\config_env_base.bat

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set IOCLOGROOT=%ICPVARDIR%/logs/ioc
for /F "usebackq" %%I in (`cygpath %IOCLOGROOT%`) do SET IOCCYGLOGROOT=%%I

set CDSVR_CONSOLEPORT=9013

@echo Starting collision detection (console port %CDSVR_CONSOLEPORT%)
set CDSVR_CMD=%MYDIRCDSVR%start_collision_detection_cmd.bat

REM Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

%ICPTOOLS%\cygwin_bin\procServ.exe --logstamp --logfile="%IOCCYGLOGROOT%/CDSVR-%%Y%%m%%d.log" --timefmt="%%c" --restrict --ignore="^D^C" --name=CDSVR --pidfile="/cygdrive/c/windows/temp/EPICS_CDSVR.pid" %CDSVR_CONSOLEPORT% %CDSVR_CMD% 
