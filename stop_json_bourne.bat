@echo off

set MYDIR=%~dp0
REM kill procservs that manage process, which in turn terminates the process

set CSPID=
for /F %%i in ( c:\windows\temp\EPICS_JSONBOURNE.pid ) DO set CSPID=%%i
if "%CSPID%" == "" (
    @echo JSON bourne procServ is not running
) else (
    @echo Killing JSON bourne procServ PID %CSPID%
    %ICPTOOLS%\cygwin_bin\cygwin_kill.exe %CSPID%
    del c:\windows\temp\EPICS_JSONBOURNE.pid
)

