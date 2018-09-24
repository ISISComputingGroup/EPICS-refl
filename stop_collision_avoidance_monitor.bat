@echo off
setlocal
set MYDIR=%~dp0
REM kill procservs that manage process, which in turn terminates the process

set CSPID=
for /F %%i in ( c:\windows\temp\EPICS_CDSVR.pid ) DO set CSPID=%%i
if "%CSPID%" == "" (
    @echo Collision Avoidance procServ is not running
) else (
    @echo Killing Collision Avoidance Monitor procServ PID %CSPID%
    caput %MYPVPREFIX%COLLIDE:MODE 4
	sleep 5
	%ICPTOOLS%\cygwin_bin\cygwin_kill.exe %CSPID%
    del c:\windows\temp\EPICS_CDSVR.pid
)

