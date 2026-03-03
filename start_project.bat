@echo off
title Deforestation Detection System - Launcher
echo ================================================
echo   Deforestation Detection System - Starting...
echo ================================================
echo.

REM --- Start Backend API Server in a new window
echo [1/3] Starting Backend API Server on http://127.0.0.1:8001 ...
start "Backend API Server" cmd /k "cd /d "%~dp0backend" && "%~dp0.venv\Scripts\activate.bat" && python -m uvicorn api_server:app --host 127.0.0.1 --port 8001 --reload"

echo [2/3] Waiting for backend to initialise + load ML model...
echo        (First run may download ~100MB BigEarthNet model weights - please wait)
timeout /t 8 /nobreak >nul

REM --- Start Frontend Dev Server in a new window
echo [3/3] Starting Frontend (Vite) on http://localhost:5173 ...
start "Frontend Dev Server" cmd /k "cd /d "%~dp0Frontend" && npm run dev"

echo.
echo ================================================
echo   Both servers are starting in separate windows.
echo   Backend  : http://127.0.0.1:8001
echo   Frontend : http://localhost:5173
echo ------------------------------------------------
echo   Machine Learning starts AUTOMATICALLY with
echo   the backend. If it shows "Offline", wait a
echo   few seconds and click "Refresh ML Status".
echo   (First run downloads model - takes ~1 min)
echo ================================================
echo.
echo   Close this window at any time.
echo   To stop the servers, close their windows.
pause
