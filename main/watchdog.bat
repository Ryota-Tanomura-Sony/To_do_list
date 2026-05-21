@echo off
setlocal
cd /d "%~dp0"

rem === watchdog.bat ===
rem 5分ごとにPanel プロセスの存在確認し、停止していれば再起動する。
rem curlのリダイレクト誤判定を避けるため、プロセス存在確認方式に変更。

set INTERVAL=300
set APPDIR=%~dp0
set LOGFILE=%~dp0watchdog.log

:LOOP
timeout /t %INTERVAL% /nobreak >nul

rem panel プロセスが存在するか確認（PowerShell使用）
powershell -NoProfile -Command "if (Get-Process -Name panel -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1

if %ERRORLEVEL%==0 (
    rem panel が動いている → 何もしない
    goto LOOP
)

rem panel が見つからない → 再起動
echo [%DATE% %TIME%] Panel not found - restarting... >> "%LOGFILE%"

rem 念のためポート5006を掃除
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5006 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>nul
)

timeout /t 3 /nobreak >nul
start /B "" cmd /c "%APPDIR%start_server.bat"
echo [%DATE% %TIME%] Restart initiated >> "%LOGFILE%"

goto LOOP
