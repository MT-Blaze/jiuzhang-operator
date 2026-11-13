@echo off
setlocal EnableExtensions
title Jiuzhang Operator - one-click installer

rem ============================================================
rem  Jiuzhang Operator - one-click installer (Windows)
rem
rem  Usage: create a BRAND-NEW EMPTY folder, put this file in it,
rem  then double-click it. It downloads the clean base release and
rem  the plugin source repo from a mirror (never github.com
rem  directly), assembles two sibling folders, writes the
rem  migration guide, and starts the base launcher.
rem
rem  Layout after install:
rem    <this folder>\
rem      jiuzhang-operator\    base (start.bat, app, static...)
rem      jiuzhang-plugins\     plugin repo (src/org.jiuzhang.*)
rem      migration guide txt
rem
rem  The base zip is a GitHub Release asset, NOT the main branch
rem  source: releases/latest/download/jiuzhang-operator.zip. The
rem  plugin repo is pure front-end source, so its main branch zip
rem  is still used. The base discovers the sibling plugin source
rem  through ../jiuzhang-plugins/src (app/core/config.py).
rem
rem  Downloads go through curl.exe, shipped with Windows 10 1803+
rem  and every Windows 11. `curl -f -L --progress-bar -o <file>`
rem  draws a live progress bar, so the black console never looks
rem  frozen while a multi-megabyte zip is on the wire. A non-zero
rem  exit code means that mirror failed and the next mirror runs.
rem
rem  Mirrors are tried in order:
rem    1. https://ghproxy.net/https://github.com/...
rem    2. https://github.kkgithub.com/...
rem    3. https://gh-proxy.com/https://github.com/...
rem    4. https://ghfast.top/https://github.com/...
rem  If all four fail, nothing is installed and you can re-run
rem  this file.
rem
rem  Keep this file pure ASCII + CRLF: cmd.exe on Chinese Windows
rem  garbles UTF-8 batch files. The Chinese prompt lines are
rem  carried as base64 and printed by PowerShell's Write-Host,
rem  which writes Unicode straight to the console whatever the
rem  active code page is.
rem ============================================================

cd /d "%~dp0"

echo ============================================================
echo   Jiuzhang Operator - one-click installer
echo ============================================================
echo.

rem The folder must be brand new. The last three checks keep a
rem legacy single-folder install from being overwritten.
if exist "%~dp0jiuzhang-operator" goto not_empty
if exist "%~dp0jiuzhang-plugins" goto not_empty
if exist "%~dp0start.bat" goto not_empty
if exist "%~dp0app\main.py" goto not_empty
if exist "%~dp0plugins" goto not_empty

set "TMPROOT=%TEMP%\jzo-install"
set "OP_ZIP=%TMPROOT%\jiuzhang-operator.zip"
set "PL_ZIP=%TMPROOT%\jiuzhang-plugins.zip"
set "OP_DIR=%TMPROOT%\operator"
set "PL_DIR=%TMPROOT%\plugins"
set "OP_DST=%~dp0jiuzhang-operator"
set "PL_DST=%~dp0jiuzhang-plugins"

if exist "%TMPROOT%" rmdir /s /q "%TMPROOT%"
mkdir "%TMPROOT%"
if not exist "%TMPROOT%" goto no_temp

where curl.exe >nul 2>&1
if errorlevel 1 goto no_curl

rem say: [1/5] downloading the base release package, may take 1-2 minutes
call :say "WzEvNV0g5q2j5Zyo5LiL6L295bqV5bqn5Y+R6KGM5YyF77yM5qC55o2u5oKo55qE572R57uc5Y+v6IO96ZyA6KaBIDEtMiDliIbpkp/vvIzor7fogJDlv4PnrYnlvoUuLi4="
call :download operator "%OP_ZIP%"
if errorlevel 1 goto download_failed

rem say: [2/5] downloading the plugin pack, may take 1-2 minutes
call :say "WzIvNV0g5q2j5Zyo5LiL6L295o+S5Lu25YyF77yM5qC55o2u5oKo55qE572R57uc5Y+v6IO96ZyA6KaBIDEtMiDliIbpkp/vvIzor7fogJDlv4PnrYnlvoUuLi4="
call :download plugins "%PL_ZIP%"
if errorlevel 1 goto download_failed

rem say: [3/5] extracting the packages
call :say "WzMvNV0g5q2j5Zyo6Kej5Y6L5a6J6KOF5YyFLi4u"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%OP_ZIP%' -DestinationPath '%OP_DIR%' -Force"
if errorlevel 1 goto extract_failed
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath '%PL_ZIP%' -DestinationPath '%PL_DIR%' -Force"
if errorlevel 1 goto extract_failed

rem The release zip has one top-level folder; the plugin main zip
rem has jiuzhang-plugins-main. Detect by content, not by name, so
rem a repo rename does not break the installer.
set "OP_SRC="
for /d %%D in ("%OP_DIR%\*") do if exist "%%~fD\start.bat" if exist "%%~fD\app\main.py" set "OP_SRC=%%~fD"
if not defined OP_SRC goto extract_failed

set "PL_SRC="
for /d %%D in ("%PL_DIR%\*") do if exist "%%~fD\src\org.jiuzhang.bank-engine\plugin.toml" set "PL_SRC=%%~fD"
if not defined PL_SRC goto extract_failed

rem say: [4/5] assembling the two sibling folders
call :say "WzQvNV0g5q2j5Zyo6KOF6YWN5bqV5bqn5LiO5o+S5Lu255uu5b2VLi4u"
mkdir "%OP_DST%" 2>nul
xcopy "%OP_SRC%\*" "%OP_DST%\" /E /H /Y /Q >nul
if errorlevel 1 goto copy_failed
if not exist "%OP_DST%\start.bat" goto copy_failed

rem Keep the whole plugin repo tree (src, plugins, plugins.json):
rem the base probes ../jiuzhang-plugins/src, no hand copying.
mkdir "%PL_DST%" 2>nul
xcopy "%PL_SRC%\*" "%PL_DST%\" /E /H /Y /Q >nul
if errorlevel 1 goto copy_failed
if not exist "%PL_DST%\src\org.jiuzhang.bank-engine\plugin.toml" goto copy_failed

rem say: [5/5] writing the migration guide
call :say "WzUvNV0g5q2j5Zyo5YaZ5YWl5pWw5o2u6L+B56e76K+05piOLi4u"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$n=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('5aaC5L2V6L+B56e75pen5pWw5o2uLnR4dA==')); $t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('5Lmd56ug566X5a2Q77ya5aaC5L2V6L+B56e75pen5pWw5o2uCgrmlrDniYjmiorlupXluqflkozmj5Lku7bliIbmiJDkuKTkuKrlubPnuqfmlofku7blpLnvvIzoo4Xlpb3lkI7nmoTnu5PmnoTmmK/vvJoKCiAg5pys5paH5Lu25aS5ICAgIOKUnOKUgCBqaXV6aGFuZy1vcGVyYXRvclwgICAg5bqV5bqn77yIc3RhcnQuYmF044CBYXBw44CBc3RhdGlj44CBZGF0YSDpg73lnKjov5nph4zvvIkKICAgIOKUlOKUgCBqaXV6aGFuZy1wbHVnaW5zXCAgICAg5o+S5Lu25rqQ56CB77yI5bqV5bqn5Lya6Ieq5Yqo6K+G5Yir77yM5LiN55So5omL5Yqo5pCs77yJCgrlpoLmnpzkvaDkuYvliY3nlKjov4fml6fniYjmnKzvvIzpopjlupPlkozmlZnlrabmlbDmja7pg73lnKjml6fniYjmnKznmoQgZGF0YSDmlofku7blpLnph4zjgIIKCui/geenu+atpemqpO+8mgoxLiDlhYjlhbPpl63mraPlnKjov5DooYznmoTkuZ3nq6DnrpflrZDvvIjlj6/lnKjml6fniYjmnKznm67lvZXnmoTlnLDlnYDmoI/ovpPlhaUgY21k77yM5omn6KGMIHN0YXJ0LmJhdCAtLXN0b3DvvInjgIIKMi4g5omT5byA5pys5paH5Lu25aS56YeM55qEIGppdXpoYW5nLW9wZXJhdG9yIOaWh+S7tuWkue+8jOaKiuaXp+eJiOacrOagueebruW9leS4i+eahCBkYXRhIOaWh+S7tuWkuQogICDmlbTkuKrlpI3liLbov5vmnaXvvIzlkozov5nph4znmoQgZGF0YSDlkIjlubbvvIjmj5DnpLropobnm5bml7bpgInmi6nigJzmmK/igJ3vvInjgIIKICAg6L+B56e75ZCO55qE5L2N572u77ya5pys5paH5Lu25aS5XGppdXpoYW5nLW9wZXJhdG9yXGRhdGEKMy4g5Y+M5Ye75pys5paH5Lu25aS5XGppdXpoYW5nLW9wZXJhdG9yXHN0YXJ0LmJhdCDlkK/liqjjgIIKNC4g5omT5byA5ZCO5qC45a+56aKY55uu5pWw6YeP5LiO5Lul5YmN5LiA6Ie044CCCgror7TmmI7vvJoKLSBkYXRhIOaYr+S9oOeahOi0ouS6p++8mumimOW6k+OAgeWbvueJh+OAgemFjee9ruOAgeWkh+S7vemDveWcqCBqaXV6aGFuZy1vcGVyYXRvclxkYXRhIOmHjOOAggotIOS7peWQjuWNh+e6p+WPquabv+aNoiBqaXV6aGFuZy1vcGVyYXRvciDkuI4gaml1emhhbmctcGx1Z2lucyDkuKTkuKrku6PnoIHmlofku7blpLnvvIwKICDnu53kuI3opoHliqggaml1emhhbmctb3BlcmF0b3JcZGF0YeOAggotIOaPkuS7tuS7o+eggee7n+S4gOS7jiBqaXV6aGFuZy1wbHVnaW5zXHNyYyDor7vlj5bvvIzkuI3pnIDopoHlpI3liLbliLDliKvlpITjgIIK')); [IO.File]::WriteAllText((Join-Path (Get-Location) $n), $t, (New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 goto guide_failed

rmdir /s /q "%TMPROOT%"

echo.
echo ============================================================
echo   Install complete. Starting Jiuzhang Operator...
echo ============================================================
call "%~dp0jiuzhang-operator\start.bat"
exit /b 0

rem ---------- download with mirror fallback ----------
:download
set "KIND=%~1"
set "DEST=%~2"
set "REL=jiuzhang-operator"
set "ASSET=releases/latest/download/jiuzhang-operator.zip"
if /i "%KIND%"=="plugins" set "REL=jiuzhang-plugins"
if /i "%KIND%"=="plugins" set "ASSET=archive/refs/heads/main.zip"
call :try_mirror "https://ghproxy.net/https://github.com/MT-Blaze/%REL%/%ASSET%" "%DEST%"
if not errorlevel 1 exit /b 0
rem say: mirror 1 failed, switching to mirror 2
call :say "W+mUmeivr10g6ZWc5YOPIDEg5LiL6L295aSx6LSl77yM5q2j5Zyo5YiH5o2i6ZWc5YOPIDIuLi4="
call :try_mirror "https://github.kkgithub.com/MT-Blaze/%REL%/%ASSET%" "%DEST%"
if not errorlevel 1 exit /b 0
rem say: mirror 2 failed, switching to mirror 3
call :say "W+mUmeivr10g6ZWc5YOPIDIg5LiL6L295aSx6LSl77yM5q2j5Zyo5YiH5o2i6ZWc5YOPIDMuLi4="
call :try_mirror "https://gh-proxy.com/https://github.com/MT-Blaze/%REL%/%ASSET%" "%DEST%"
if not errorlevel 1 exit /b 0
rem say: mirror 3 failed, switching to mirror 4
call :say "W+mUmeivr10g6ZWc5YOPIDMg5LiL6L295aSx6LSl77yM5q2j5Zyo5YiH5o2i6ZWc5YOPIDQuLi4="
call :try_mirror "https://ghfast.top/https://github.com/MT-Blaze/%REL%/%ASSET%" "%DEST%"
if not errorlevel 1 exit /b 0
exit /b 1

:try_mirror
set "URL=%~1"
set "DEST=%~2"
if exist "%DEST%" del /f /q "%DEST%" >nul 2>&1
echo   GET %URL%
curl.exe -f -L --progress-bar --connect-timeout 20 --max-time 900 -o "%DEST%" "%URL%"
if errorlevel 1 exit /b 1
if not exist "%DEST%" exit /b 1
for %%A in ("%DEST%") do if %%~zA LSS 100000 exit /b 1
exit /b 0

rem ---------- unicode console output ----------
rem Prints one UTF-8 message, carried as base64, so the batch file
rem itself stays pure ASCII. Write-Host goes through the Unicode
rem console API, so the Chinese shows up in a GBK code page too.
:say
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Write-Host ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%~1')))"
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

rem say: this Windows has no curl.exe, needs Windows 10 1803+
:no_curl
echo.
call :say "W+mUmeivr10g5pys5py65rKh5pyJIGN1cmwuZXhl44CC6K+35L2/55SoIFdpbmRvd3MgMTAgMTgwMyDlj4rku6XkuIrniYjmnKzvvIzmiJblhYjku47lhbbku5bnlLXohJHmi4nlj5blronoo4XljIXjgII="
echo.
pause
exit /b 1

:download_failed
echo.
rem say: all four mirrors failed, check network and re-run
call :say "W+mUmeivr10g5Zub5Liq6ZWc5YOP6IqC54K55YWo6YOo5LiL6L295aSx6LSl44CC6K+35qOA5p+l572R57uc5oiW5Luj55CG5ZCO77yM6YeN5paw5Y+M5Ye7IGluc3RhbGwuYmF044CC"
echo.
rmdir /s /q "%TMPROOT%" 2>nul
pause
exit /b 1

:extract_failed
echo.
echo [ERROR] The downloaded package is incomplete or has an unexpected layout.
echo         Delete the folder contents and run install.bat again.
echo.
rmdir /s /q "%TMPROOT%" 2>nul
pause
exit /b 1

:copy_failed
echo.
echo [ERROR] Copying files into this folder failed.
echo         Close any program that may lock this folder, then run again.
echo.
if exist "%OP_DST%" rmdir /s /q "%OP_DST%" 2>nul
if exist "%PL_DST%" rmdir /s /q "%PL_DST%" 2>nul
rmdir /s /q "%TMPROOT%" 2>nul
pause
exit /b 1

:guide_failed
echo.
echo [WARN] Files are installed, but the migration guide could not be written.
echo        The installer will still start the program.
echo.
pause
call "%~dp0jiuzhang-operator\start.bat"
exit /b 0
