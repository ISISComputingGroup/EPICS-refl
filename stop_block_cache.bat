@echo off

set MYDIR=%~dp0
REM kill procservs that manage process, which in turn terminates the process

set CSPID=
for /F %%i in ( c:\windows\temp\EPICS_BLOCKCACHE.pid ) DO set CSPID=%%i
if "%CSPID%" == "" (
    @echo blockcache procServ is not running
) else (
    @echo Killing blockcache procServ PID %CSPID%
    %ICPTOOLS%\cygwin_bin\cygwin_kill.exe %CSPID%
    del c:\windows\temp\EPICS_BLOCKCACHE.pid
)

