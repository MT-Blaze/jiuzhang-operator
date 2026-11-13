@echo off
setlocal EnableExtensions
title Jiuzhang Operator - build release package

rem ============================================================
rem  Jiuzhang Operator - release package builder (Windows)
rem  Double-click to produce a clean, redistributable zip in dist\.
rem
rem  This package is the RUNTIME tree only. Plugin source lives in
rem  the sibling repository and install.bat puts it next to the base
rem  as jiuzhang-plugins\; the base discovers it through
rem  ../jiuzhang-plugins/src (app/core/config.py). The release zip
rem  therefore never carries plugins\.
rem
rem  Strips dev / heavy / generated content:
rem    .env, .venv, .git, .github, data, plugins, tests, tools,
rem    scripts, examples, docs, .qoder, caches, logs, root notes,
rem    installer scripts, any *.db and backup sidecars.
rem
rem  Keeps everything a receiver needs to run:
rem    app, static, start.bat, requirements.txt, plugins.toml,
rem    README, LICENSE, .env.example and the static showcase page.
rem
rem  Output:
rem    dist\jiuzhang-operator-v<VER>.zip  versioned release asset
rem    dist\jiuzhang-operator.zip         stable asset name for
rem                                       releases/latest/download
rem  Upload BOTH files to the same GitHub Release: install.bat
rem  fetches the stable name, humans read the versioned name.
rem
rem  The dist\ output folder is git-ignored; nothing here is committed.
rem  Receiver: create an empty folder, drop install.bat in it, double-click
rem            (needs Python 3.10+ and internet on first run).
rem ============================================================

cd /d "%~dp0"

rem ---------- Step 0: read version from app\__init__.py ----------
set "VER=beta"
for /f "usebackq tokens=3 delims= " %%v in (`findstr /b /c:"__version__" "%~dp0app\__init__.py"`) do set "VER=%%~v"
set "RELNAME=jiuzhang-operator-v%VER%"
set "STAGE=%TEMP%\%RELNAME%"
set "OUTDIR=%~dp0dist"
set "ZIP=%OUTDIR%\%RELNAME%.zip"
set "STABLE=%OUTDIR%\jiuzhang-operator.zip"

echo ============================================================
echo   Building %RELNAME%.zip
echo ============================================================
echo.

rem ---------- Step 1: clean staging ----------
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"

rem ---------- Step 2: copy runtime tree, excluding dev / heavy / generated ----------
echo [1/4] Copying runtime files...
robocopy "%~dp0." "%STAGE%" /E /NFL /NDL /NJH /NJS /NP ^
  /XD .venv venv .git .github .pytest_cache .system_generated __pycache__ node_modules .ruff_cache .mypy_cache .idea .vscode .scratch* "%~dp0dist" "%~dp0data" "%~dp0plugins" "%~dp0tests" "%~dp0tools" "%~dp0scripts" "%~dp0examples" "%~dp0docs" "%~dp0.qoder" ^
  /XF .env *.log *.pyc *.pyo Thumbs.db .DS_Store *.db *.db-shm *.db-wal *.db-journal *.bak backup_*.zst manifest_*.json "%~dp0examples\template-plugin.zip" install.bat build_release.bat .gitignore .gitattributes
if errorlevel 8 (
    echo.
    echo [ERROR] File copy failed. Nothing was packaged.
    echo         Close any program locking the folder, then run again.
    echo.
    pause
    exit /b 1
)

rem Root notes and reports are for developers only. Keep README.md as
rem the one human entry and requirements.txt as the dependency list.
for %%F in ("%STAGE%\*.md") do if /i not "%%~nxF"=="README.md" del /f /q "%%~F" >nul 2>&1
for %%F in ("%STAGE%\*.txt") do if /i not "%%~nxF"=="requirements.txt" del /f /q "%%~F" >nul 2>&1

rem ---------- Step 3: verify the package is pure and runnable ----------
echo [2/4] Verifying clean layout...
set "MISSING="
for %%F in ("%STAGE%\start.bat" "%STAGE%\requirements.txt" "%STAGE%\LICENSE" "%STAGE%\README.md" "%STAGE%\app\main.py" "%STAGE%\static\index.html") do if not exist "%%~F" set "MISSING=%%~F"
if defined MISSING (
    echo.
    echo [ERROR] Required runtime file missing: %MISSING%
    echo.
    pause
    exit /b 1
)
if exist "%STAGE%\tests" goto impure
if exist "%STAGE%\tools" goto impure
if exist "%STAGE%\scripts" goto impure
if exist "%STAGE%\plugins" goto impure
if exist "%STAGE%\data" goto impure
if exist "%STAGE%\.qoder" goto impure

rem ---------- Step 4: zip the staging folder (single top-level dir) ----------
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
copy /Y "%ZIP%" "%STABLE%" >nul
if not exist "%STABLE%" (
    echo.
    echo [ERROR] Cannot create the stable asset name jiuzhang-operator.zip.
    echo.
    pause
    exit /b 1
)

rem ---------- Step 5: clean up staging ----------
echo [4/4] Cleaning up...
rmdir /s /q "%STAGE%"

echo.
echo ============================================================
echo   DONE.
echo   Versioned: %ZIP%
echo   Stable:    %STABLE%
echo ============================================================
echo   Upload BOTH files to the SAME GitHub Release.
echo   install.bat downloads the stable name from
echo   releases/latest/download/jiuzhang-operator.zip.
echo   No .env, no data, no .venv, no tests, no plugins inside.
echo.
pause
endlocal
exit /b 0

:impure
echo.
echo [ERROR] Developer files leaked into the package staging folder.
echo         Nothing was packaged. Check the /XD exclude list.
echo.
pause
exit /b 1
