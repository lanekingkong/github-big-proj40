@echo off
echo ============================================
echo   AgentForge - Windows Installer
echo ============================================
echo.

echo [1/3] Installing Node.js dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed
    pause
    exit /b 1
)

echo [2/3] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)

echo [3/3] Creating environment file...
if not exist .env (
    copy .env.example .env >nul 2>&1
    echo Created .env from .env.example
)

echo.
echo ============================================
echo   Installation complete!
echo   Run: npm run dev
echo ============================================
pause
