@echo off
echo Starting AI Logistics System...

echo [1/2] Starting Backend Server...
start "AI Logistics Backend" cmd /k "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting Frontend UI...
start "AI Logistics Frontend" cmd /k "cd frontend && npm run dev"

echo Both servers are starting up! 
echo Close these windows to stop the servers.
