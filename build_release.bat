@echo off
setlocal EnableExtensions
title Jiuzhang Operator - build beta package

rem ============================================================
rem  Jiuzhang Operator - beta package builder (Windows)
rem  Double-click to produce a clean, redistributable zip in dist\.
rem
rem  Strips secrets and heavy/generated content:
rem    .env, .venv, venv, data, .git, caches, logs, .system_generated,
rem    plugins\org.jiuzhang.demo-bank (runtime seed install; source is examples\demo_plugin.zip),
rem    plugin bodies must never bloat the base package - see plugins.json index
rem    .scratch-recon-063\ and any .scratch*\ (v0.6.3: dev recon sandbox holding a READ-ONLY COPY of
rem    the legacy third-party database - clean-room rule 1 forbids shipping it, and it is git-ignored too)
rem    plugins\org.jiuzhang.bank-engine\bank\v063.db + v063_migrated.db (v0.6.3: structural baseline and
rem    migration build artifacts; the runtime seed is bank.db only, so 1.7 MB of duplicate dbs stay out)
rem    plugins\org.jiuzhang.core-bank\ (retired by order #20: only local bank.db / .bak leftovers remain
rem    on this dev machine; engine + bank-ui replace it, and the 456-question seed must never ship)
rem  Keeps everything a receiver needs to run:
rem    app, static, schemas, plugins, examples, docs, tests,
rem    start.bat, requirements.txt, README and the guides, .env.example
rem
rem  The dist\ output folder is git-ignored; nothing here is committed.
rem  Receiver: extract the zip, then double-click start.bat
rem            (needs Python 3.11+ and internet on first run).
rem ============================================================

cd /d "%~dp0"

rem ---------- Step 0: read version from app\__init__.py ----------
set "VER=beta"
for /f "usebackq tokens=3 delims= " %%v in (`findstr /b /c:"__version__" "%~dp0app\__init__.py"`) do set "VER=%%~v"
set "RELNAME=jiuzhang-operator-beta-v%VER%"
set "STAGE=%TEMP%\%RELNAME%"
set "OUTDIR=%~dp0dist"
set "ZIP=%OUTDIR%\%RELNAME%.zip"

echo ============================================================
echo   Building %RELNAME%.zip
echo ============================================================
echo.

rem ---------- Step 1: clean staging ----------
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"

rem ---------- Step 2: copy tree, excluding sensitive / heavy / generated ----------
echo [1/3] Copying project files (excluding secrets, venv, data, caches)...
rem  Bare names exclude that dir anywhere; full paths pin data/dist to the repo
rem  root only, so a plugin's own dist\ assets are never stripped by mistake.
robocopy "%~dp0." "%STAGE%" /E /NFL /NDL /NJH /NJS /NP ^
  /XD .venv venv .git .pytest_cache .system_generated __pycache__ node_modules .ruff_cache .mypy_cache .idea .vscode .scratch-recon-063 .scratch* "%~dp0dist" "%~dp0data" "%~dp0plugins\org.jiuzhang.demo-bank" "%~dp0plugins\org.jiuzhang.core-bank" "%~dp0plugins\org.jiuzhang.bank-engine\bank\assets" ^
  /XF .env *.log *.pyc *.pyo Thumbs.db .DS_Store *.db-shm *.db-wal *.db-journal *.bak backup_*.zst manifest_*.json "%~dp0examples\template-plugin.zip" "%~dp0plugins\org.jiuzhang.bank-engine\bank\v063_migrated.db" "%~dp0plugins\org.jiuzhang.bank-engine\bank\v063.db" "%~dp0plugins\org.jiuzhang.bank-engine\bank\bank.db"
if errorlevel 8 (
    echo.
    echo [ERROR] File copy failed. Nothing was packaged.
    echo         Close any program locking the folder, then run again.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 2b: ship a PURE empty seed (ADR-003) ----------
rem The real 456-question bank.db stays on THIS dev machine only. The redistributable
rem ships the frozen empty baseline (v063.db, ~155 KB, 0 rows) as bank.db so a fresh
rem receiver opens an empty library and builds it up through the Workspace selector.
copy /Y "%~dp0plugins\org.jiuzhang.bank-engine\bank\v063.db" "%STAGE%\plugins\org.jiuzhang.bank-engine\bank\bank.db" >nul
if not exist "%STAGE%\plugins\org.jiuzhang.bank-engine\bank\bank.db" (
    echo.
    echo [ERROR] Empty seed not staged - v063.db baseline is missing in the source tree.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 3: zip the staging folder (single top-level dir) ----------
echo [2/3] Compressing...
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
if exist "%ZIP%" del "%ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath '%STAGE%' -DestinationPath '%ZIP%' -Force"
if not exist "%ZIP%" (
    echo.
    echo [ERROR] Compression failed - the zip was not created.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 4: clean up staging ----------
echo [3/3] Cleaning up...
rmdir /s /q "%STAGE%"

echo.
echo ============================================================
echo   DONE: %ZIP%
echo ============================================================
echo   Ship this zip. No .env, no data, no .venv inside.
echo   Receiver extracts it and double-clicks start.bat.
echo.
pause
endlocal
