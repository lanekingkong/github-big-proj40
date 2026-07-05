@echo off
echo Starting AgentForge development environment...
echo.

:: Start backend
echo Starting Python backend...
start "AgentForge Backend" cmd /k "cd backend && python main.py"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start frontend
echo Starting Electron + React dev server...
call npm run dev

pause
