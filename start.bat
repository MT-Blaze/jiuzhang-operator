@echo off
setlocal EnableExtensions
title Jiuzhang Operator

rem ============================================================
rem  Jiuzhang Operator - one-click launcher (Windows)
rem  Double-click this file to start. Keep this window open
rem  while you use the app. Closing this window stops the server.
rem  Full instructions: see the Markdown install guide in this folder.
rem
rem  Self-healing ladder, walked top to bottom (no admin rights,
rem  no hand editing, no "call me and I will fix it" steps):
rem    1. no venv          -> create one
rem    2. no pip in venv   -> ensurepip, then rebuild the venv
rem    3. deps fail        -> retry other package sources
rem    4. port taken       -> serve on the next free port
rem ============================================================

cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "LASTPORT=8009"
set "VENV_PY=.venv\Scripts\python.exe"

echo ============================================================
echo   Jiuzhang Operator - starting up
echo ============================================================
echo.

rem ---------- Step 1: locate or create the virtual environment ----------
if exist "%VENV_PY%" (
    echo [1/5] Virtual environment found.
    goto pipcheck
)

echo [1/5] Creating virtual environment ^(first run only^)...
py -3 -m venv .venv 2>nul
if not exist "%VENV_PY%" python -m venv .venv 2>nul
if exist "%VENV_PY%" goto pipcheck

echo.
echo [ERROR] Could not create a virtual environment.
echo         Please install Python 3.11 or newer from
echo         https://www.python.org/downloads/  ^(check "Add to PATH"^),
echo         then double-click start.bat again.
echo.
pause
exit /b 1

:pipcheck
rem ---------- Step 2: make sure pip works inside that venv ----------
rem  A venv can be born without pip: a stripped or offline Python,
rem  "venv --without-pip", or a first run that was interrupted halfway.
rem  Without this step the launcher dies on "No module named pip" and
rem  the user sees a wall of red text with no way out.
"%VENV_PY%" -m pip --version >nul 2>&1
if not errorlevel 1 goto deps

echo [2/5] pip is missing inside .venv - repairing with ensurepip...
"%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
"%VENV_PY%" -m pip --version >nul 2>&1
if not errorlevel 1 goto deps

echo         ensurepip did not fix it. Rebuilding .venv from scratch...
rmdir /s /q .venv 2>nul
py -3 -m venv .venv 2>nul
if not exist "%VENV_PY%" python -m venv .venv 2>nul
if not exist "%VENV_PY%" goto pip_broken
"%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
"%VENV_PY%" -m pip --version >nul 2>&1
if not errorlevel 1 goto deps

:pip_broken
echo.
echo [ERROR] Could not get a working pip inside .venv.
echo         Reinstall Python 3.11 or newer from
echo         https://www.python.org/downloads/  ^(keep "Add to PATH"
echo         and the bundled pip option checked^), delete the .venv
echo         folder next to this file, then double-click start.bat again.
echo.
pause
exit /b 1

:deps
rem ---------- Step 3: install dependencies ----------
echo [3/5] Installing dependencies ^(needs internet on first run^)...
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt
if not errorlevel 1 goto deps_ok

rem  Attempt 2: a domestic mirror. On Chinese networks the official
rem  index is usually the slow or failing one, so try a well stocked
rem  mirror here before falling back to pypi.org. None of these retries
rem  loosen the version pins in requirements.txt.
echo.
echo         First source failed. Retrying from a domestic mirror:
echo         https://pypi.tuna.tsinghua.edu.cn/simple
echo.
"%VENV_PY%" -m pip install --disable-pip-version-check --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
if not errorlevel 1 goto deps_ok

rem  Attempt 3: the official source, in case the default or the mirror
rem  is stale and has not synced one of the pinned versions yet.
echo.
echo         Mirror failed too. Retrying from the official source:
echo         https://pypi.org/simple
echo.
"%VENV_PY%" -m pip install --disable-pip-version-check --index-url https://pypi.org/simple -r requirements.txt
if not errorlevel 1 goto deps_ok

echo.
echo [ERROR] Dependency installation failed on every source.
echo         Check your internet connection or proxy settings,
echo         then double-click start.bat again.
echo.
pause
exit /b 1

:deps_ok
rem ---------- Step 4: pick a port nobody is listening on ----------
rem  If an older copy of the app is still running on 8000, uvicorn
rem  cannot bind and the browser keeps talking to that OLD instance -
rem  old pages, old version number, confusing everyone. Serving on the
rem  next free port keeps the double-click telling the truth.
echo [4/5] Looking for a free port ...
set "FREEPORT="
for /l %%p in (%PORT%,1,%LASTPORT%) do (
    if not defined FREEPORT (
        netstat -ano -p TCP 2>nul | findstr /c:":%%p " | findstr /c:"LISTENING" >nul
        if errorlevel 1 set "FREEPORT=%%p"
    )
)
if defined FREEPORT goto port_picked

echo.
echo [ERROR] Every port from %PORT% to %LASTPORT% is already in use.
echo         Close the programs holding them ^(or reboot^), then
echo         double-click start.bat again.
echo.
pause
exit /b 1

:port_picked
if "%FREEPORT%"=="%PORT%" goto port_set
echo         Port %PORT% is busy - most likely an older Jiuzhang window
echo         is still open. Serving on %FREEPORT% instead so you are
echo         looking at THIS copy, not the old one.
echo         Close that old window if you want port %PORT% back.

:port_set
set "PORT=%FREEPORT%"
set "URL=http://%HOST%:%PORT%"

rem ---------- Step 5: open the browser once the server is up ----------
echo [5/5] Opening your browser at %URL% ...
start "" /min cmd /c "timeout /t 4 /nobreak >nul && start %URL%"

echo.
echo         Starting server. KEEP THIS WINDOW OPEN.
echo.
echo         App:       %URL%
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
