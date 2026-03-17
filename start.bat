@echo off
REM ============================================================
REM NewLearner - One-click startup script (Windows)
REM ============================================================
REM Starts: backend API + frontend dev server
REM Optional: CLIProxyAPI proxy (if LLM_MODE=setup-token in .env)
REM ============================================================

setlocal enabledelayedexpansion

REM --- Check .env ---
if not exist ".env" (
    echo [ERROR] .env file not found. Creating from .env.example ...
    copy .env.example .env
    echo [INFO] Please edit .env to configure your settings, then re-run this script.
    pause
    exit /b 1
)

REM --- Read LLM_MODE from .env ---
set LLM_MODE=api-key
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "key=%%A"
    REM Skip comments
    echo !key! | findstr /b "#" >nul && (
        REM skip
    ) || (
        if "%%A"=="LLM_MODE" set "LLM_MODE=%%B"
    )
)

echo ============================================================
echo  NewLearner - Starting services
echo  LLM Mode: %LLM_MODE%
echo ============================================================

REM --- Start CLIProxyAPI if setup-token mode ---
if "%LLM_MODE%"=="setup-token" (
    echo.
    echo [1/3] Starting CLIProxyAPI proxy on localhost:8317 ...
    if not exist "C:\cliproxyapi\cli-proxy-api.exe" (
        echo [ERROR] cli-proxy-api.exe not found at C:\cliproxyapi\cli-proxy-api.exe
        echo         Please make sure CLIProxyAPI is installed at C:\cliproxyapi\
        pause
        exit /b 1
    )
    start "CLIProxyAPI" cmd /c "C:\cliproxyapi\cli-proxy-api.exe --config C:\cliproxyapi\config.yaml 2>&1"
    timeout /t 2 /nobreak >nul
    echo [OK] CLIProxyAPI proxy started.
) else (
    echo.
    echo [1/3] Skipping proxy (api-key mode)
)

REM --- Start backend ---
echo.
echo [2/3] Starting FastAPI backend on localhost:8000 ...
start "NewLearner-Backend" cmd /c "call conda activate research_tools && python -m src.api.app 2>&1"
timeout /t 3 /nobreak >nul
echo [OK] Backend started.

REM --- Start frontend ---
echo.
echo [3/3] Starting React frontend on localhost:5173 ...
start "NewLearner-Frontend" cmd /c "cd frontend && npm run dev 2>&1"
timeout /t 3 /nobreak >nul
echo [OK] Frontend started.

echo.
echo ============================================================
echo  All services running!
echo  Open: http://localhost:5173
echo.
echo  To stop: close the terminal windows or press Ctrl+C in each.
echo ============================================================
echo.
pause
