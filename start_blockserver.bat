REM @echo off

REM set MYDIRBLOCK=%~dp0
REM call %MYDIRBLOCK%stop_blockserver.bat
REM set CYGWIN=nodosfilewarning
REM call %MYDIRBLOCK%..\..\..\config_env_base.bat

REM set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
REM set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

REM set IOCLOGROOT=%ICPVARDIR%/logs/ioc
REM for /F "usebackq" %%I in (`cygpath %IOCLOGROOT%`) do SET IOCCYGLOGROOT=%%I

REM set BLOCKSERVER_CONSOLEPORT=9006

REM @echo Starting blockserver (console port %BLOCKSERVER_CONSOLEPORT%)
REM set BLOCKSERVER_CMD=%MYDIRBLOCK%start_blockserver_cmd.bat

REM Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

REM %ICPTOOLS%\cygwin_bin\procServ.exe --logstamp --logfile="%IOCCYGLOGROOT%/BLOCKSVR-%%Y%%m%%d.log" --timefmt="%%c" --restrict --ignore="^D^C" --name=BLOCKSVR --pidfile="/cygdrive/c/windows/temp/EPICS_BLOCKSVR.pid" %BLOCKSERVER_CONSOLEPORT% %BLOCKSERVER_CMD% 
