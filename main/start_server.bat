@echo off
setlocal
rem === ToDo App - Panel サーバー起動スクリプト ===
rem ブラウザで http://localhost:5007 を開いてください

set "APPDIR=%~dp0"
set "PANEL=C:\Users\0107409306\AppData\Local\miniconda3\Scripts\panel.exe"

cd /d "%APPDIR%"

if not exist "%PANEL%" (
    echo [ERROR] panel.exe not found: "%PANEL%"
    exit /b 1
)

"%PANEL%" serve To_do.py ^
    --port 5007 ^
    --address 127.0.0.1 ^
    --allow-websocket-origin=localhost:5007 ^
    --num-threads 2 ^
    --check-unused-sessions 60000 ^
    --unused-session-lifetime 900000 ^
    --liveness ^
    --keep-alive 30000

endlocal
