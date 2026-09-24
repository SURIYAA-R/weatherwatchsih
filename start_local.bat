@echo off
title WeatherWatch Local Deployment
echo ===================================================
echo Starting WeatherWatch Full Stack Locally...
echo ===================================================

echo [1/2] Launching Backend API (Port 8000)...
start "WeatherWatch Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Launching Frontend Web App (Port 3000)...
start "WeatherWatch Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 3000"

timeout /t 2 >nul
echo.
echo ===================================================
echo WeatherWatch is running!
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo ===================================================
start http://localhost:3000
