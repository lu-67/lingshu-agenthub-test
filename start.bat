@echo off
title AgentHub Launcher
set "PYDIR=D:\software\Python 3.10.11"
set "NODEDIR=C:\Users\33464\.workbuddy\binaries\node\versions\22.22.2-6"
set "PATH=%PYDIR%;%NODEDIR%;%PATH%"

echo Starting AgentHub...
echo   Backend  -^> http://127.0.0.1:8000
echo   Frontend -^> http://127.0.0.1:5173
echo.

start "AgentHub Backend :8000" /D "D:\nexus-agent\agent-core" cmd /k python run_server.py
start "AgentHub Frontend :5173" /D "D:\nexus-agent\frontend" cmd /k npm run dev

echo Waiting 10 seconds for both services...
timeout /t 10 /nobreak >nul
start "" http://127.0.0.1:5173

echo.
echo Login   : tester / tester123   (admin / admin123)
echo Swagger : http://127.0.0.1:8000/docs
echo Close the two CMD windows to stop the services.
echo.
pause
