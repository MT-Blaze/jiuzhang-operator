@echo off
setlocal
title Jiuzhang Operator

rem ============================================================
rem  Jiuzhang Operator - one-click launcher (Windows)
rem  Double-click this file to start. Keep this window open
rem  while you use the app. Closing this window stops the server.
rem  Full instructions: see the Markdown install guide in this folder.
rem ============================================================

cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "URL=http://%HOST%:%PORT%"
set "VENV_PY=.venv\Scripts\python.exe"

echo ============================================================
echo   Jiuzhang Operator - starting up
echo ============================================================
echo.

rem ---------- Step 1: locate or create the virtual environment ----------
if exist "%VENV_PY%" (
    echo [1/4] Virtual environment found.
    goto deps
)

echo [1/4] Creating virtual environment ^(first run only^)...
py -3 -m venv .venv 2>nul
if not exist "%VENV_PY%" python -m venv .venv 2>nul
if not exist "%VENV_PY%" (
    echo.
    echo [ERROR] Could not create a virtual environment.
    echo         Please install Python 3.11 or newer from
    echo         https://www.python.org/downloads/  ^(check "Add to PATH"^),
    echo         then double-click start.bat again.
    echo.
    pause
    exit /b 1
)

:deps
rem ---------- Step 2: install dependencies ----------
echo [2/4] Installing dependencies ^(needs internet on first run^)...
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed.
    echo         Check your internet connection, then double-click
    echo         start.bat again.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 3: open the browser once the server is up ----------
echo [3/4] Opening your browser at %URL% ...
start "" /min cmd /c "timeout /t 4 /nobreak >nul && start %URL%"

rem ---------- Step 4: run the server in this window ----------
echo [4/4] Starting server. KEEP THIS WINDOW OPEN.
echo.
echo         App:     %URL%
echo         Questions: %URL%/questions
echo         Workspace: %URL%/workspace
echo         Plugins:   %URL%/plugins
echo.
echo         To stop: close this window, or press Ctrl+C.
echo.
"%VENV_PY%" -m uvicorn app.main:app --host %HOST% --port %PORT%

echo.
echo Server stopped. You can close this window.
pause
endlocal
