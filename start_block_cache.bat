REM @echo off

set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%stop_block_cache.bat
set CYGWIN=nodosfilewarning
call %MYDIRBLOCK%..\..\..\config_env_base.bat

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set IOCLOGROOT=%ICPVARDIR%/logs/ioc
for /F "usebackq" %%I in (`cygpath %IOCLOGROOT%`) do SET IOCCYGLOGROOT=%%I

set BLOCKCACHE_CONSOLEPORT=9011

@echo Starting BLOCKCACHE (console port %BLOCKCACHE_CONSOLEPORT%)
set BLOCKCACHE_CMD=%MYDIRBLOCK%start_block_cache_cmd.bat

REM Unlike IOC we are not using "--noautorestart --wait" so will start immediately and also automatically restart on exit

%ICPTOOLS%\cygwin_bin\procServ.exe --logstamp --logfile="%IOCCYGLOGROOT%/BLOCKCACHE-%%Y%%m%%d.log" --timefmt="%%c" --restrict --ignore="^D^C" --name=BLOCKCACHE --pidfile="/cygdrive/c/windows/temp/EPICS_BLOCKCACHE.pid" %BLOCKCACHE_CONSOLEPORT% %BLOCKCACHE_CMD% 
