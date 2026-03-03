@echo off
REM تشغيل سيرفر Flask
start "Flask Server" cmd /k ".venv\Scripts\python.exe app.py"
REM انتظار 5 ثواني للتأكد من تشغيل السيرفر
ping 127.0.0.1 -n 6 > nul
REM تشغيل LocalTunnel
start "LocalTunnel" cmd /k "npx localtunnel --port 5000 --subdomain smartparking-rafal"
