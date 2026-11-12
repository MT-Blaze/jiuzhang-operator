@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  Jiuzhang Operator - THE ONE official launcher (Windows)
rem
rem  Double-click this file. It does everything by itself:
rem    1. relaunches itself in a hidden window (the black box
rem       flashes once and is gone)
rem    2. stops only THIS project's old python/uvicorn processes
rem       (never any other Python program on the computer)
rem    3. starts the server silently on 127.0.0.1:65496
rem    4. waits until /healthz answers, then opens the browser
rem       at http://127.0.0.1:65496/e
rem
rem  The port is fixed at 65496 on purpose: one project, one port.
rem  If a foreign program owns 65496, this launcher reports it and
rem  stops - it never kills that program and never moves to another
rem  port (moving ports was the root cause of "I edited code but saw
rem  an old page").
rem
rem  To stop the server without starting a new one, run:
rem      start.bat --stop
rem
rem  All output goes to data\launcher.log.
rem ============================================================

rem ---------- stage 0: hide this console ----------
if /i "%~1"=="--run" goto run
if /i "%~1"=="--stop" goto stop
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Process -FilePath '%~f0' -ArgumentList '--run' -WindowStyle Hidden"
exit /b 0

rem ---------- optional: stop the server (start.bat --stop) ----------
:stop
set "LOG=data\launcher.log"
if not exist "data" mkdir "data"
call :log "--stop requested"
call :kill_project_servers
call :log "server stopped"
exit /b 0

:run
set "HOST=127.0.0.1"
set "PORT=65496"
set "URL=http://%HOST%:%PORT%"
set "ENTRY=%URL%/e"
set "HEALTH=%URL%/healthz"
set "VENV_PY=.venv\Scripts\python.exe"
set "LOG=data\launcher.log"

if not exist "data" mkdir "data"
call :log "================ launcher start ================"

rem ---------- stage 1: virtual environment ----------
if exist "%VENV_PY%" goto pipcheck
call :log "creating .venv (first run only)"
py -3 -m venv .venv 2>nul
if not exist "%VENV_PY%" python -m venv .venv 2>nul
if not exist "%VENV_PY%" goto no_python

:pipcheck
"%VENV_PY%" -m pip --version >nul 2>&1
if not errorlevel 1 goto deps
call :log "pip missing - repairing with ensurepip"
"%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
"%VENV_PY%" -m pip --version >nul 2>&1
if not errorlevel 1 goto deps
call :log "ensurepip failed - rebuilding .venv"
rmdir /s /q .venv 2>nul
py -3 -m venv .venv 2>nul
if not exist "%VENV_PY%" python -m venv .venv 2>nul
if not exist "%VENV_PY%" goto no_python
"%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
"%VENV_PY%" -m pip --version >nul 2>&1
if not errorlevel 1 goto deps
goto no_python

rem ---------- stage 2: dependencies ----------
:deps
call :log "checking dependencies"
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt >>"%LOG%" 2>&1
if not errorlevel 1 goto deps_ok
call :log "default index failed - retrying domestic mirror"
"%VENV_PY%" -m pip install --disable-pip-version-check --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt >>"%LOG%" 2>&1
if not errorlevel 1 goto deps_ok
call :log "mirror failed - retrying official pypi"
"%VENV_PY%" -m pip install --disable-pip-version-check --index-url https://pypi.org/simple -r requirements.txt >>"%LOG%" 2>&1
if not errorlevel 1 goto deps_ok
goto deps_failed

rem ---------- stage 3: stop old instances of THIS project ONLY ----------
rem  Scope is the command line: only python/pythonw/uvicorn processes
rem  whose CommandLine contains this folder's absolute path are killed.
rem  A stray python from another project never matches, so it survives.
:deps_ok
call :log "stopping old Jiuzhang python/uvicorn processes"
call :kill_project_servers

rem  Give Windows a moment to release the socket, then make sure the
rem  port is really free. If something foreign still holds it, bail out.
"%SystemRoot%\System32\ping.exe" -n 2 127.0.0.1 >nul
netstat -ano -p TCP | findstr ":65496" | findstr "LISTENING" >nul
if not errorlevel 1 goto port_busy

rem ---------- stage 4: start the server silently ----------
call :log "starting hidden uvicorn on port 65496"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a=@('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','65496'); Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList $a -WorkingDirectory '%~dp0' -WindowStyle Hidden -RedirectStandardOutput '%~dp0data\uvicorn-65496.out.log' -RedirectStandardError '%~dp0data\uvicorn-65496.err.log'"

rem ---------- stage 5: wait for health, then open the browser ----------
call :log "waiting for %HEALTH%"
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$entry='%ENTRY%'; $health='%HEALTH%'; for ($i=0; $i -lt 240; $i++) { try { $r=Invoke-WebRequest -UseBasicParsing -Uri $health -TimeoutSec 2; if ($r.StatusCode -eq 200) { Start-Process $entry; exit 0 } } catch { }; Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 goto start_failed
call :log "browser opened: %ENTRY%"
call :log "launcher done"
exit /b 0

:port_busy
call :log "ERROR: port 65496 is held by a foreign program"
powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Port 65496 is already used by another program. Close that program (it is NOT Jiuzhang Operator), then double-click start.bat again.','Jiuzhang Operator')"
exit /b 1

:no_python
call :log "ERROR: no usable Python found"
powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Python 3.10 or newer was not found. Install it from python.org with Add to PATH checked, then double-click start.bat again.','Jiuzhang Operator')"
exit /b 1

:deps_failed
call :log "ERROR: dependency installation failed on every source"
powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Could not install dependencies. Check the network or proxy, then double-click start.bat again. Details: data\launcher.log','Jiuzhang Operator')"
exit /b 1

:start_failed
call :log "ERROR: server did not answer /healthz in time"
powershell -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('The server did not answer on port 65496 within 120 seconds. See data\launcher.log and data\uvicorn-65496.err.log for details.','Jiuzhang Operator')"
exit /b 1

rem ---------- kill only THIS project's python/uvicorn ----------
:kill_project_servers
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=[IO.Path]::GetFullPath('%~dp0'); $n=0; Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|uvicorn)\.exe$' -and $_.CommandLine -and $_.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0 } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $n++ }; Add-Content -Path 'data\launcher.log' -Value ('stopped project processes: ' + $n)"
exit /b 0

rem ---------- tiny logger ----------
:log
>>"%LOG%" echo [%DATE% %TIME%] %~1
exit /b 0
