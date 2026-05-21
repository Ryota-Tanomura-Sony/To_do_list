@echo off
setlocal
cd /d "%~dp0"

rem === watchdog.bat ===
rem 5分ごとにliveness endpointを確認し、応答がなければサーバーを再起動する。
rem スタートアップフォルダに登録して使用。

set HEALTH_URL=http://localhost:5006
set INTERVAL=300

:LOOP
timeout /t %INTERVAL% /nobreak >nul

rem liveness check
curl -s -o nul -w "%%{http_code}" %HEALTH_URL% > "%TEMP%\todo_health.txt" 2>nul
set /p STATUS=<"%TEMP%\todo_health.txt"

if "%STATUS%"=="200" (
    rem サーバー正常
    goto LOOP
)

rem サーバー応答なし → 再起動
echo [%DATE% %TIME%] Server down - restarting... >> "%~dp0watchdog.log"

rem 既存プロセスを停止（ポート5006を使用しているプロセスを探す）
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5006" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>nul
)

rem 少し待ってから再起動
timeout /t 5 /nobreak >nul
start /B "" cmd /c "%~dp0start_server.bat"
echo [%DATE% %TIME%] Restart initiated >> "%~dp0watchdog.log"

goto LOOP
