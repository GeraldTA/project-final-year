@echo off
cd /d "%~dp0"
echo Starting API Server...
python -m uvicorn api_server:app --host 127.0.0.1 --port 8001 --reload
pause
