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
rem    examples\placeholder_plugin.zip (v0.5.1: distributed via CDN/proxy mirrors + online install;
rem    plugin bodies must never bloat the base package - see plugins.json index)
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
  /XD .venv venv .git .pytest_cache .system_generated __pycache__ node_modules .ruff_cache .mypy_cache .idea .vscode "%~dp0dist" "%~dp0data" "%~dp0plugins\org.jiuzhang.demo-bank" ^
  /XF .env *.log *.pyc *.pyo Thumbs.db .DS_Store "%~dp0examples\placeholder_plugin.zip"
if errorlevel 8 (
    echo.
    echo [ERROR] File copy failed. Nothing was packaged.
    echo         Close any program locking the folder, then run again.
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
