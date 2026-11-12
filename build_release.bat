@echo off
setlocal EnableExtensions
title Jiuzhang Operator - build release package

rem ============================================================
rem  Jiuzhang Operator - release package builder (Windows)
rem  Double-click to produce a clean, redistributable zip in dist\.
rem
rem  Plugin source lives in the sibling repository, never in this base repo:
rem    JZO_PLUGIN_SOURCE_DIR  (explicit)
rem    ../jiuzhang-plugins/src (default probe)
rem  The staged package carries plugins/<id>/ as the ONE global plugin
rem  directory (army order #34). Workspaces never hold plugin copies;
rem  they only hold data under data\workspaces\<id>\.
rem
rem  Strips secrets and heavy/generated content:
rem    .env, .venv, venv, data, .git, caches, logs, .system_generated,
rem    root plugins\ (source of truth is the sibling plugin repo),
rem    any *.db / *.bak / sqlite sidecars (the only db shipped is the
rem    frozen 0-question seed copied in Step 2b).
rem
rem  Keeps everything a receiver needs to run:
rem    install.bat (first-run entry), app, static, schemas, plugins,
rem    examples, docs, tests, start.bat, requirements.txt, README and
rem    the guides, .env.example
rem
rem  The dist\ output folder is git-ignored; nothing here is committed.
rem  Receiver: create an empty folder, drop install.bat in it, double-click
rem            (needs Python 3.11+ and internet on first run).
rem ============================================================

cd /d "%~dp0"

rem ---------- Step 0: read version from app\__init__.py ----------
set "VER=beta"
for /f "usebackq tokens=3 delims= " %%v in (`findstr /b /c:"__version__" "%~dp0app\__init__.py"`) do set "VER=%%~v"
set "RELNAME=jiuzhang-operator-v%VER%"
set "STAGE=%TEMP%\%RELNAME%"
set "OUTDIR=%~dp0dist"
set "ZIP=%OUTDIR%\%RELNAME%.zip"

rem ---------- Step 0b: locate plugin source ----------
set "PLUGIN_SRC=%JZO_PLUGIN_SOURCE_DIR%"
if not defined PLUGIN_SRC set "PLUGIN_SRC=%~dp0..\jiuzhang-plugins\src"
if not exist "%PLUGIN_SRC%\org.jiuzhang.bank-engine\plugin.toml" (
    echo.
    echo [ERROR] Plugin source not found: "%PLUGIN_SRC%"
    echo         Set JZO_PLUGIN_SOURCE_DIR or keep ../jiuzhang-plugins/src next to this repo.
    echo.
    pause
    exit /b 1
)
set "PLUGIN_SRC=%PLUGIN_SRC%\"

echo ============================================================
echo   Building %RELNAME%.zip
echo   Plugins: %PLUGIN_SRC%
echo ============================================================
echo.

rem ---------- Step 1: clean staging ----------
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"

rem ---------- Step 2: copy base tree, excluding sensitive / heavy / generated ----------
echo [1/4] Copying base project files...
robocopy "%~dp0." "%STAGE%" /E /NFL /NDL /NJH /NJS /NP ^
  /XD .venv venv .git .pytest_cache .system_generated __pycache__ node_modules .ruff_cache .mypy_cache .idea .vscode .scratch-recon-063 .scratch* "%~dp0dist" "%~dp0data" "%~dp0plugins" ^
  /XF .env *.log *.pyc *.pyo Thumbs.db .DS_Store *.db-shm *.db-wal *.db-journal *.bak backup_*.zst manifest_*.json "%~dp0examples\template-plugin.zip"
if errorlevel 8 (
    echo.
    echo [ERROR] File copy failed. Nothing was packaged.
    echo         Close any program locking the folder, then run again.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 2a: stage plugin source from the sibling repo ----------
echo [2/4] Staging plugin source...
robocopy "%PLUGIN_SRC%." "%STAGE%\plugins" /E /NFL /NDL /NJH /NJS /NP ^
  /XD .git __pycache__ node_modules .pytest_cache .idea .vscode ^
  /XF *.log *.pyc *.pyo Thumbs.db .DS_Store *.db *.db-shm *.db-wal *.db-journal *.bak
if errorlevel 8 (
    echo.
    echo [ERROR] Plugin source copy failed. Nothing was packaged.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 2b: ship a PURE empty seed (ADR-003) ----------
rem The real 456-question bank.db stays on the dev machine only. The redistributable
rem ships the frozen empty baseline (data\seed\v063.db, 0 rows) as bank.db so a fresh
rem receiver opens an empty library and builds it up through the Workspace selector.
if not exist "%~dp0data\seed\v063.db" (
    echo.
    echo [ERROR] Empty seed missing: data\seed\v063.db
    echo.
    pause
    exit /b 1
)
copy /Y "%~dp0data\seed\v063.db" "%STAGE%\plugins\org.jiuzhang.bank-engine\bank\bank.db" >nul
if not exist "%STAGE%\plugins\org.jiuzhang.bank-engine\bank\bank.db" (
    echo.
    echo [ERROR] Empty seed not staged - bank-engine\bank\ does not exist.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 2c: first-run entry must be present ----------
rem install.bat is the intended first-run entry for a fresh receiver:
rem empty folder -> drop install.bat -> double-click. It downloads both
rem repos from mirrors, then calls start.bat. Never ship without it.
if not exist "%STAGE%\install.bat" (
    echo.
    echo [ERROR] install.bat missing from the package - it is the first-run entry.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 3: zip the staging folder (single top-level dir) ----------
echo [3/4] Compressing...
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
echo [4/4] Cleaning up...
rmdir /s /q "%STAGE%"

echo.
echo ============================================================
echo   DONE: %ZIP%
echo ============================================================
echo   Ship this zip. No .env, no data, no .venv inside.
echo   Receiver creates an empty folder, drops install.bat in it,
echo   and double-clicks - the installer downloads both repos and
echo   calls start.bat automatically.
echo.
pause
endlocal
