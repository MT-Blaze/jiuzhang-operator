@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  Jiuzhang Operator - THE ONE official launcher (Windows)
rem
rem  Double-click this file. It does everything by itself:
rem    1. relaunches itself in a hidden window (the black box
rem       flashes once and is gone)
rem    2. probes 65496..65505 for a running Jiuzhang instance.
rem       Same folder -> opens that page and exits, so a double
rem       click can never start a second copy. Another folder ->
rem       kills the old instance and continues to a fresh start
rem    3. stops the Jiuzhang instance that owns port 65496 when
rem       the identity check above did not already handle it
rem    4. starts the server silently on 127.0.0.1:65496 and
rem       records the live port in data\.current_port
rem    5. waits until /healthz answers, then opens the browser
rem       at http://127.0.0.1:65496/e
rem
rem  The port is fixed at 65496 on purpose: one project, one port.
rem  If a foreign program owns 65496, this launcher reports its
rem  PID and process name and stops - it never kills that program
rem  and never moves to another port (moving ports was the root
rem  cause of "I edited code but saw an old page").
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
call :instance_gate stop
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

rem ---------- stage 0b: single-instance lock across install folders ----------
rem  Probe 65496..65505 plus the last used port in data\.current_port.
rem  A listener that answers /healthz with jiuzhang-operator (or carries
rem  app.main:app on that port) is a Jiuzhang instance. Same folder ->
rem  reuse it and just open the browser; another folder -> kill it and
rem  start fresh. Foreign programs are never killed.
call :instance_gate
if errorlevel 10 exit /b 0
if errorlevel 2 goto port_busy

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

rem ---------- stage 3: stop the old Jiuzhang instance on 65496 ----------
rem  Identity is the port, not the folder. The listener PID on 65496
rem  is killed only when it answers /healthz with the jiuzhang-operator
rem  service name, or its command line contains app.main:app. That
rem  catches a server left behind by another install folder, which the
rem  old path-matching logic could never see, while leaving unrelated
rem  programs alone.
:deps_ok
call :log "checking the process that owns port 65496"
call :kill_port_owner
if errorlevel 2 goto port_busy

rem  Give Windows a moment to release the socket, then make sure the
rem  port is really free. If something still holds it, bail out.
"%SystemRoot%\System32\ping.exe" -n 2 127.0.0.1 >nul
netstat -ano -p TCP | findstr ":65496" | findstr "LISTENING" >nul
if not errorlevel 1 goto port_busy

rem ---------- stage 4: start the server silently ----------
call :log "starting hidden uvicorn on port 65496"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a=@('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','65496'); Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList $a -WorkingDirectory '%~dp0' -WindowStyle Hidden -RedirectStandardOutput '%~dp0data\uvicorn-65496.out.log' -RedirectStandardError '%~dp0data\uvicorn-65496.err.log'"

rem ---------- stage 5: wait for health, then open the browser ----------
call :log "waiting for %HEALTH%"
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$entry='%ENTRY%'; $health='%HEALTH%'; for ($i=0; $i -lt 240; $i++) { try { $r=Invoke-WebRequest -UseBasicParsing -Uri $health -TimeoutSec 2; if ($r.StatusCode -eq 200) { Set-Content -Path 'data\.current_port' -Value '65496' -Encoding ASCII; Start-Process $entry; exit 0 } } catch { }; Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 goto start_failed
call :log "browser opened: %ENTRY%"
call :log "launcher done"
exit /b 0

:port_busy
set "OWN_PID=unknown"
set "OWN_NAME=unknown"
if exist "data\port-owner.pid" set /p OWN_PID=<"data\port-owner.pid"
if exist "data\port-owner.name" set /p OWN_NAME=<"data\port-owner.name"
call :log "ERROR: port 65496 is held by PID %OWN_PID% (%OWN_NAME%)"
powershell -NoProfile -WindowStyle Hidden -Command "$m=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('56uv5Y+jIDY1NDk2IOW3suiiq+WNoOeUqO+8iFBJRCB7UElEfe+8jOi/m+eoiyB7TkFNRX3vvInjgILkuZ3nq6DnrpflrZDml6Dms5XlkK/liqjvvIzor7fmiYvliqjnu5PmnZ/or6Xov5vnqIvvvIzmiJbph43lkK/nlLXohJHlkI7lho3mrKHlj4zlh7sgc3RhcnQuYmF044CC'); $m=$m.Replace('{PID}','%OWN_PID%').Replace('{NAME}','%OWN_NAME%'); Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show($m,'Jiuzhang Operator')"
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

rem ---------- single-instance gate: probe, reuse, or clean ----------
rem  Exit 0  = no running instance left; caller starts a fresh server.
rem  Exit 10 = a same-folder instance was reused and the browser opened.
rem  Exit 2  = 65496 is held by a foreign process; owner files written.
rem  With the argument "stop" every discovered Jiuzhang instance is
rem  killed (any folder) and data\.current_port is removed.
:instance_gate
del /q "data\port-owner.pid" 2>nul
del /q "data\port-owner.name" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $mode='%~1'; $root='%~dp0'; $ports=@(); if (Test-Path 'data\.current_port') { $v=0; try { $v=[int](Get-Content 'data\.current_port' -TotalCount 1) } catch { }; if ($v -ge 1024 -and $v -le 65535) { $ports += $v } }; for ($p=65496; $p -le 65505; $p++) { $ports += $p }; $ports=@($ports | Sort-Object -Unique); $found=@(); $foreign=$false; foreach ($p in $ports) { $owners=@(); try { $owners = @(Get-NetTCPConnection -LocalPort $p -State Listen | Select-Object -ExpandProperty OwningProcess) } catch { }; if ($owners.Count -eq 0) { continue }; $op=[int]$owners[0]; $proc=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $op); $isJz=$false; $body=''; try { $r=Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $p + '/healthz') -TimeoutSec 2; $body=[string]$r.Content } catch { }; if ($body -match 'jiuzhang-operator') { $isJz=$true }; if (-not $isJz -and $proc -and $proc.Name -match '^(python|pythonw|uvicorn)\.exe$' -and $proc.CommandLine -and $proc.CommandLine.IndexOf('app.main:app') -ge 0 -and $proc.CommandLine.IndexOf('--port ' + $p) -ge 0) { $isJz=$true }; if (-not $isJz) { if ($p -eq 65496) { $foreign=$true; Set-Content -Path 'data\port-owner.pid' -Value ([string]$op) -Encoding ASCII; $nm='unknown'; if ($proc -and $proc.Name) { $nm=$proc.Name }; Set-Content -Path 'data\port-owner.name' -Value ($nm -replace '[^A-Za-z0-9_.\-]','_') -Encoding ASCII }; continue }; $same=$false; if ($proc -and $proc.CommandLine -and $proc.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0) { $same=$true }; if (-not $same -and $proc -and $proc.ExecutablePath -and $proc.ExecutablePath.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0) { $same=$true }; if (-not $same -and $proc) { $cur=$proc; for ($i=0; $i -lt 4; $i++) { if (-not $cur.ParentProcessId) { break }; $cur=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $cur.ParentProcessId); if (-not $cur) { break }; if ($cur.Name -notmatch '^(python|pythonw|uvicorn)\.exe$') { break }; if (($cur.CommandLine -and $cur.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0) -or ($cur.ExecutablePath -and $cur.ExecutablePath.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0)) { $same=$true; break } } }; $found += [pscustomobject]@{Port=$p; Pid=$op; SameDir=$same} }; if ($mode -eq 'stop') { foreach ($f in $found) { $t=@($f.Pid); $cur=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $f.Pid); for ($i=0; $i -lt 4; $i++) { if (-not $cur.ParentProcessId) { break }; $cur=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $cur.ParentProcessId); if (-not $cur) { break }; if ($cur.Name -match '^(python|pythonw|uvicorn)\.exe$' -and $cur.CommandLine -and $cur.CommandLine.IndexOf('app.main:app') -ge 0 -and $cur.CommandLine.IndexOf('--port ' + $f.Port) -ge 0) { $t += $cur.ProcessId } else { break } }; foreach ($x in $t) { taskkill /F /T /PID $x | Out-Null } }; Start-Sleep -Milliseconds 800; Remove-Item 'data\.current_port' -Force; Add-Content -Path 'data\launcher.log' -Value ('stopped jiuzhang instances: ' + $found.Count + ' (foreign port 65496: ' + $foreign + ')'); exit 0 }; if ($found.Count -eq 0) { if ($foreign) { exit 2 }; exit 0 }; $reuse=$found | Where-Object { $_.SameDir } | Sort-Object Port | Select-Object -First 1; if ($reuse) { foreach ($f in $found) { if ($f.Port -ne $reuse.Port) { taskkill /F /T /PID $f.Pid | Out-Null } }; Set-Content -Path 'data\.current_port' -Value ([string]$reuse.Port) -Encoding ASCII; Add-Content -Path 'data\launcher.log' -Value ('reused running instance on port ' + $reuse.Port); Start-Process ('http://127.0.0.1:' + $reuse.Port + '/e'); exit 10 }; for ($round=0; $round -lt 3; $round++) { $alive=@(); foreach ($f in $found) { if (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $f.Pid)) { $alive += $f } }; if ($alive.Count -eq 0) { break }; foreach ($f in $alive) { $t=@($f.Pid); $cur=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $f.Pid); for ($i=0; $i -lt 4; $i++) { if (-not $cur.ParentProcessId) { break }; $cur=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $cur.ParentProcessId); if (-not $cur) { break }; if ($cur.Name -match '^(python|pythonw|uvicorn)\.exe$' -and $cur.CommandLine -and $cur.CommandLine.IndexOf('app.main:app') -ge 0 -and $cur.CommandLine.IndexOf('--port ' + $f.Port) -ge 0) { $t += $cur.ProcessId } else { break } }; foreach ($x in $t) { taskkill /F /T /PID $x | Out-Null } }; Start-Sleep -Milliseconds 500; $next=@(); foreach ($f in $found) { $o=@(); try { $o = @(Get-NetTCPConnection -LocalPort $f.Port -State Listen | Select-Object -ExpandProperty OwningProcess) } catch { }; if ($o.Count -gt 0) { $next += [pscustomobject]@{Port=$f.Port; Pid=[int]$o[0]; SameDir=$false} } }; $found=$next; if ($found.Count -eq 0) { break } }; Add-Content -Path 'data\launcher.log' -Value ('cleaned other-folder jiuzhang instances, left: ' + $found.Count); if ($foreign) { exit 2 }; exit 0"
if errorlevel 10 exit /b 10
if errorlevel 2 exit /b 2
exit /b 0

rem ---------- kill the port 65496 owner only when it is Jiuzhang ----------
rem  Exit 0 when the port is free or a Jiuzhang owner was killed.
rem  Exit 2 when the port is still held; data\port-owner.pid and
rem  data\port-owner.name are written for the error dialog.
:kill_port_owner
del /q "data\port-owner.pid" 2>nul
del /q "data\port-owner.name" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $port=65496; $pids=@(); try { $pids += @(Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -ExpandProperty OwningProcess) } catch { }; if ($pids.Count -eq 0) { $rows = netstat -ano -p TCP | Select-String (':' + $port + '\s') | Select-String 'LISTENING'; foreach ($row in $rows) { $f = @($row.Line -split '\s+' | Where-Object { $_ -ne '' }); if ($f.Count -ge 5) { $pids += [int]$f[4] } } }; $pids = @($pids | Sort-Object -Unique); if ($pids.Count -eq 0) { exit 0 }; $alive=@(); foreach ($p in $pids) { if (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $p)) { $alive += $p } }; if ($alive.Count -eq 0) { exit 0 }; $body=''; try { $r = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $port + '/healthz') -TimeoutSec 2; $body = [string]$r.Content } catch { }; $isJz = ($body -match 'jiuzhang-operator'); if (-not $isJz) { foreach ($p in $alive) { $proc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $p); if ($proc.Name -match '^(python|pythonw|uvicorn)\.exe$' -and $proc.CommandLine -and $proc.CommandLine.IndexOf('app.main:app') -ge 0) { $isJz = $true } } }; $writeOwner = { param($p) $proc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $p); $name = 'unknown'; if ($proc -and $proc.Name) { $name = $proc.Name }; Set-Content -Path 'data\port-owner.pid' -Value ([string]$p) -Encoding ASCII; Set-Content -Path 'data\port-owner.name' -Value ($name -replace '[^A-Za-z0-9_.\-]','_') -Encoding ASCII }; if (-not $isJz) { & $writeOwner $alive[0]; exit 2 }; $kids = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|uvicorn)\.exe$' -and $_.CommandLine -and $_.CommandLine.IndexOf('app.main:app') -ge 0 -and $_.CommandLine.IndexOf('--port ' + $port) -ge 0 } | Select-Object -ExpandProperty ProcessId); $all = @($alive + $kids | Sort-Object -Unique); foreach ($p in $all) { taskkill /F /T /PID $p | Out-Null }; for ($i=0; $i -lt 40; $i++) { $still = @(); try { $still = @(Get-NetTCPConnection -LocalPort $port -State Listen) } catch { }; if ($still.Count -eq 0) { break }; Start-Sleep -Milliseconds 500 }; $still = @(); try { $still = @(Get-NetTCPConnection -LocalPort $port -State Listen) } catch { }; if ($still.Count -gt 0) { & $writeOwner ([int]$still[0].OwningProcess); exit 2 }; Add-Content -Path 'data\launcher.log' -Value ('killed jiuzhang port owners: ' + ($all -join ',')); exit 0"
if errorlevel 2 exit /b 2
exit /b 0

rem ---------- tiny logger ----------
:log
>>"%LOG%" echo [%DATE% %TIME%] %~1
exit /b 0
