@echo off
setlocal
cd /d "%~dp0"
rem === watchdog.bat ===
rem 5分ごとにポート5007の監視をし、停止していれば再起動する。
set "INTERVAL=300"
set "LOGFILE=%~dp0watchdog.log"

:LOOP
timeout /t %INTERVAL% /nobreak >nul
netstat -aon 2>nul | findstr ":5007 " | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL%==0 goto LOOP
echo [%DATE% %TIME%] Panel not found - restarting... >> "%LOGFILE%"
timeout /t 3 /nobreak >nul
start /B "" cmd /c "%~dp0start_server.bat"
echo [%DATE% %TIME%] Restart initiated >> "%LOGFILE%"
goto LOOP
