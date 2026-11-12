@echo off
setlocal EnableExtensions
title Jiuzhang Operator - one-click installer

rem ============================================================
rem  Jiuzhang Operator - one-click installer (Windows)
rem
rem  Usage: create a BRAND-NEW EMPTY folder, put this file in it,
rem  then double-click it. It downloads both repositories from a
rem  mirror (never github.com directly), unpacks them into this
rem  folder, writes the migration guide, and starts start.bat.
rem
rem  Layout after install:
rem    <this folder>\            base project (app, static, start.bat...)
rem    <this folder>\plugins\    plugin source (org.jiuzhang.*)
rem
rem  Mirrors are tried in order, each with a timeout:
rem    1. https://ghproxy.net/https://github.com/...
rem    2. https://github.kkgithub.com/...
rem    3. https://gh-proxy.com/https://github.com/...
rem    4. https://ghfast.top/https://github.com/...
rem  If all fail, nothing is installed and you can re-run this file.
rem
rem  Keep this file pure ASCII + CRLF: cmd.exe on Chinese Windows
rem  garbles UTF-8 batch files.
rem ============================================================

cd /d "%~dp0"

echo ============================================================
echo   Jiuzhang Operator - one-click installer
echo ============================================================
echo.

if exist "%~dp0start.bat" goto not_empty
if exist "%~dp0app\main.py" goto not_empty
if exist "%~dp0plugins" goto not_empty

set "TMPROOT=%TEMP%\jzo-install"
set "OP_ZIP=%TMPROOT%\jiuzhang-operator.zip"
set "PL_ZIP=%TMPROOT%\jiuzhang-plugins.zip"
set "OP_DIR=%TMPROOT%\operator"
set "PL_DIR=%TMPROOT%\plugins"

if exist "%TMPROOT%" rmdir /s /q "%TMPROOT%"
mkdir "%TMPROOT%"
if not exist "%TMPROOT%" goto no_temp

echo [1/5] Downloading Jiuzhang Operator (main branch)...
call :download operator "%OP_ZIP%"
if errorlevel 1 goto download_failed

echo [2/5] Downloading Jiuzhang plugins (main branch)...
call :download plugins "%PL_ZIP%"
if errorlevel 1 goto download_failed

echo [3/5] Extracting...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%OP_ZIP%' -DestinationPath '%OP_DIR%' -Force"
if errorlevel 1 goto extract_failed
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%PL_ZIP%' -DestinationPath '%PL_DIR%' -Force"
if errorlevel 1 goto extract_failed

set "OP_SRC="
for /d %%D in ("%OP_DIR%\*") do set "OP_SRC=%%~fD"
if not defined OP_SRC goto extract_failed
if not exist "%OP_SRC%\start.bat" goto extract_failed

set "PL_SRC=%PL_DIR%\jiuzhang-plugins-main\src"
if not exist "%PL_SRC%\org.jiuzhang.bank-engine\plugin.toml" goto extract_failed

echo [4/5] Installing files...
xcopy "%OP_SRC%\*" "%~dp0" /E /H /Y /Q >nul
if errorlevel 1 goto copy_failed
mkdir "%~dp0plugins" 2>nul
xcopy "%PL_SRC%\*" "%~dp0plugins\" /E /H /Y /Q >nul
if errorlevel 1 goto copy_failed

echo [5/5] Writing the migration guide...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$n=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('5aaC5L2V6L+B56e75pen5pWw5o2uLnR4dA==')); $t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('5Lmd56ug566X5a2Q77ya5aaC5L2V6L+B56e75pen5pWw5o2uCgrlpoLmnpzkvaDkuYvliY3nlKjov4fml6fniYjmnKzvvIzpopjlupPlkozmlZnlrabmlbDmja7pg73lnKjml6fniYjmnKznmoQgZGF0YSDmlofku7blpLnph4zjgIIKCui/geenu+atpemqpO+8mgoxLiDlhYjlhbPpl63mraPlnKjov5DooYznmoTkuZ3nq6DnrpflrZDvvIjlj6/ov5DooYzml6fniYjmnKznm67lvZXph4znmoQgc3RhcnQuYmF0IC0tc3RvcO+8ieOAggoyLiDmiorml6fniYjmnKzmoLnnm67lvZXkuIvnmoQgZGF0YSDmlofku7blpLnmlbTkuKrlpI3liLbliLDmnKzmlofku7blpLnvvIzopobnm5blkIzlkI3mlofku7blpLnjgIIKICAg5aaC5p6c5o+Q56S65ZCI5bm25oiW5pu/5o2i77yM6YCJ5oup4oCc5piv4oCd44CCCjMuIOWPjOWHu+acrOaWh+S7tuWkuemHjOeahCBzdGFydC5iYXQg5ZCv5Yqo44CCCjQuIOaJk+W8gOWQjuaguOWvuemimOebruaVsOmHj+S4juS7peWJjeS4gOiHtOOAggoK6K+05piO77yaCi0gZGF0YSDmmK/kvaDnmoTotKLkuqfvvJrpopjlupPjgIHlm77niYfjgIHphY3nva7jgIHlpIfku73pg73lnKjph4zpnaLjgIIKLSDmlrDniYjmnKzpppbmrKHlkK/liqjkvJroh6rliqjooaXlu7rnvLrlpLHnm67lvZXvvIzkuI3kvJrmlLnliqjkvaDmi7fov5vmnaXnmoTmlbDmja7jgIIKLSDml6fniYjmnKzoi6Xmm77miormj5Lku7bku6PnoIHlpI3liLbov5sgZGF0YSDph4znmoTlt6XkvZzljLrnm67lvZXvvIzmlrDniYjmnKzkvJrlv73nlaXlroPvvJsKICDmj5Lku7bku6PnoIHnu5/kuIDku47mnKzmlofku7blpLnnmoQgcGx1Z2lucyDor7vlj5bvvIzml6DpnIDmiYvliqjmuIXnkIbjgIIK')); [IO.File]::WriteAllText((Join-Path (Get-Location) $n), $t, (New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 goto guide_failed

rmdir /s /q "%TMPROOT%"

echo.
echo ============================================================
echo   Install complete. Starting Jiuzhang Operator...
echo ============================================================
call "%~dp0start.bat"
exit /b 0

rem ---------- download with mirror fallback ----------
:download
set "KIND=%~1"
set "DEST=%~2"
set "REL=jiuzhang-operator"
if /i "%KIND%"=="plugins" set "REL=jiuzhang-plugins"
call :try_mirror "https://ghproxy.net/https://github.com/MT-Blaze/%REL%/archive/refs/heads/main.zip" "%DEST%"
if not errorlevel 1 exit /b 0
echo   Mirror 1 failed - switching to mirror 2...
call :try_mirror "https://github.kkgithub.com/MT-Blaze/%REL%/archive/refs/heads/main.zip" "%DEST%"
if not errorlevel 1 exit /b 0
echo   Mirror 2 failed - switching to mirror 3...
call :try_mirror "https://gh-proxy.com/https://github.com/MT-Blaze/%REL%/archive/refs/heads/main.zip" "%DEST%"
if not errorlevel 1 exit /b 0
echo   Mirror 3 failed - switching to mirror 4...
call :try_mirror "https://ghfast.top/https://github.com/MT-Blaze/%REL%/archive/refs/heads/main.zip" "%DEST%"
if not errorlevel 1 exit /b 0
exit /b 1

:try_mirror
set "URL=%~1"
set "DEST=%~2"
if exist "%DEST%" del /f /q "%DEST%" >nul 2>&1
echo   GET %URL%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%DEST%' -TimeoutSec 180 -MaximumRedirection 10; exit 0 } catch { Write-Host ('  download error: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 exit /b 1
if not exist "%DEST%" exit /b 1
for %%A in ("%DEST%") do if %%~zA LSS 100000 exit /b 1
exit /b 0

rem ---------- failure paths ----------
:not_empty
echo.
echo [ERROR] This folder is not empty.
echo         Create a brand-new empty folder, put install.bat in it,
echo         then double-click it. Existing data is never touched.
echo.
pause
exit /b 1

:no_temp
echo.
echo [ERROR] Cannot create a temporary folder under %TEMP%.
echo         Check free disk space or clean %TEMP%, then run again.
echo.
pause
exit /b 1

:download_failed
echo.
echo [ERROR] All download mirrors failed.
echo         Check the network or proxy, then double-click install.bat again.
echo.
pause
exit /b 1

:extract_failed
echo.
echo [ERROR] The downloaded package is incomplete or has an unexpected layout.
echo         Delete the folder contents and run install.bat again.
echo.
pause
exit /b 1

:copy_failed
echo.
echo [ERROR] Copying files into this folder failed.
echo         Close any program that may lock this folder, then run again.
echo.
pause
exit /b 1

:guide_failed
echo.
echo [WARN] Files are installed, but the migration guide could not be written.
echo        The installer will still start the program.
echo.
pause
call "%~dp0start.bat"
exit /b 0
