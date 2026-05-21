@echo off
setlocal
cd /d "%~dp0"

rem === ToDo App - Panel サーバー起動スクリプト ===
rem ブラウザで http://localhost:5006 を開いてください
rem ログイン情報は credentials.json で管理しています（ユーザー名: admin）

set PANEL=C:\Users\0107409306\AppData\Local\miniconda3\Scripts\panel.exe

"%PANEL%" serve To_do.py ^
    --basic-auth credentials.json ^
    --cookie-secret 56d86929a4314d8a9720938daeba9ce6e6cb3d947dd157fb65a1e3c9ff85c33d ^
    --port 5006 ^
    --address 127.0.0.1 ^
    --allow-websocket-origin=localhost:5006

endlocal
