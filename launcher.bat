@echo off
title Hotel Compare - Service Manager
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "INSTALL_DIR=%~dp0"
if "!INSTALL_DIR:~-1!"=="\" set "INSTALL_DIR=!INSTALL_DIR:~0,-1!"
set "LOGFILE=!INSTALL_DIR!\launcher_log.txt"

:: Init log (use system encoding, no chcp 65001)
echo ======================================== > "!LOGFILE!"
echo Hotel Compare Launcher Log >> "!LOGFILE!"
echo Install: !INSTALL_DIR! >> "!LOGFILE!"
echo ======================================== >> "!LOGFILE!"

call :LOG "Launcher started"

:MENU
cls
echo(
echo  =============================================
echo    Hotel Compare - Service Manager
echo  =============================================
echo(
echo    Install: !INSTALL_DIR!
echo(

:: Check service status via temp file
set "FOUND_PID="
set "_NS=%TEMP%\hc_ns_%RANDOM%.txt"
netstat -ano > "!_NS!" 2>nul
for /f "tokens=5" %%p in ('findstr /c:":8888 " "!_NS!" ^| findstr /c:"LISTENING"') do (
    if not "%%p"=="" set "FOUND_PID=%%p"
)
del "!_NS!" 2>nul

if not "!FOUND_PID!"=="" (
    echo    Status:  [RUNNING]  PID: !FOUND_PID!
    echo    Web UI:  http://127.0.0.1:8888
    call :LOG "Status: RUNNING PID !FOUND_PID!"
) else (
    echo    Status:  [STOPPED]
    call :LOG "Status: STOPPED"
)
echo(
echo  =============================================
echo(
echo    [1] Start Service
echo    [2] Stop Service
echo    [3] Restart Service
echo    [4] Open Web UI
echo(
echo    [5] Create Desktop Shortcut
echo    [6] View Log
echo    [7] Uninstall
echo(
echo    [0] Exit
echo(
echo  =============================================
echo(

set "CHOICE="
set /p "CHOICE=  Select [0-7]: "
call :LOG "User: !CHOICE!"

if "!CHOICE!"=="1" goto :START
if "!CHOICE!"=="2" goto :STOP
if "!CHOICE!"=="3" goto :RESTART
if "!CHOICE!"=="4" goto :OPEN_UI
if "!CHOICE!"=="5" goto :SHORTCUT
if "!CHOICE!"=="6" goto :VIEW_LOG
if "!CHOICE!"=="7" goto :UNINSTALL
if "!CHOICE!"=="0" goto :EXIT
goto :MENU

:START
echo(
call :LOG "=== START ==="

:: Check already running
call :CHECK_PORT
if not "!FOUND_PID!"=="" (
    echo  [!] Already running on 8888 (PID !FOUND_PID!)
    call :LOG "Already running PID !FOUND_PID!"
    echo(
    pause
    goto :MENU
)

:: Find Python
set "PY_CMD="
if exist "!INSTALL_DIR!\venv\Scripts\python.exe" (
    set "PY_CMD=!INSTALL_DIR!\venv\Scripts\python.exe"
    goto :FOUND_PY
)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
    goto :FOUND_PY
)
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3"
    goto :FOUND_PY
)

echo  [X] Python not found
call :LOG "ERROR: no Python"
echo      Install: https://apps.microsoft.com/detail/9P7QFQMJRFP7
echo(
pause
goto :MENU

:FOUND_PY
echo  [*] Python: !PY_CMD!
echo  [*] Starting service...
call :LOG "Python: !PY_CMD!"

:: Write a helper bat to avoid quote escaping hell
set "LAUNCH_BAT=%TEMP%\hc_start_%RANDOM%.bat"
(
echo @echo off
echo cd /d "!INSTALL_DIR!"
echo "!PY_CMD!" main.py --web ^> "!INSTALL_DIR!\service_log.txt" 2^>^&1
echo echo.
echo echo Service stopped. Press any key...
echo pause ^>nul
) > "!LAUNCH_BAT!"

start "HotelCompareWeb" "!LAUNCH_BAT!"
call :LOG "Launched via helper bat"

:: Wait for port
echo  [*] Waiting for port 8888...
set /a "WAIT=0"
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a "WAIT+=1"

call :CHECK_PORT
if not "!FOUND_PID!"=="" (
    echo  [OK] Service started (PID !FOUND_PID!)
    call :LOG "Up after !WAIT!s PID !FOUND_PID!"
    timeout /t 1 /nobreak >nul
    start "" "http://127.0.0.1:8888"
    goto :MENU
)

if !WAIT! geq 20 (
    echo  [!] Timeout (20s) - service failed to start
    call :LOG "ERROR: timeout 20s"
    echo(
    if exist "!INSTALL_DIR!\service_log.txt" (
        echo  --- service_log.txt (last 15 lines) ---
        powershell -NoProfile -Command "Get-Content '!INSTALL_DIR!\service_log.txt' -Tail 15"
        echo  --- end ---
    ) else (
        echo  No service_log.txt found.
        echo  Try running manually:
        echo    cd !INSTALL_DIR!
        echo    python main.py --web
    )
    echo(
    pause
    goto :MENU
)
goto :WAIT_LOOP

:STOP
echo(
call :LOG "=== STOP ==="
set "KILLED=0"
call :CHECK_PORT
if not "!FOUND_PID!"=="" (
    call :LOG "Kill PID !FOUND_PID!"
    taskkill /pid !FOUND_PID! /f >nul 2>&1
    set "KILLED=1"
)
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
:: Also kill any helper bat
for %%f in ("%TEMP%\hc_start_*.bat") do taskkill /fi "windowtitle eq %%~nf*" /f >nul 2>&1

if "!KILLED!"=="1" (
    echo  [OK] Stopped
    call :LOG "Stopped"
) else (
    echo  [!] Not running
    call :LOG "Not running"
)
echo(
pause
goto :MENU

:RESTART
call :LOG "=== RESTART ==="
call :STOP_SILENT
echo  [*] Restarting...
timeout /t 2 /nobreak >nul
goto :START

:STOP_SILENT
call :CHECK_PORT
if not "!FOUND_PID!"=="" (
    taskkill /pid !FOUND_PID! /f >nul 2>&1
)
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
goto :eof

:OPEN_UI
start "" "http://127.0.0.1:8888"
call :LOG "Opened browser"
echo  [OK] Browser opened
timeout /t 2 /nobreak >nul
goto :MENU

:SHORTCUT
echo(
call :LOG "Creating shortcut..."
set "PS_SCRIPT=%TEMP%\hc_shortcut.ps1"

(
echo $ws = New-Object -ComObject WScript.Shell
echo $desktop = [Environment]::GetFolderPath('Desktop'^)
echo $lnk = $ws.CreateShortcut("$desktop\Hotel Compare.lnk"^)
echo $lnk.TargetPath = Join-Path '!INSTALL_DIR!' 'launcher.bat'
echo $lnk.WorkingDirectory = '!INSTALL_DIR!'
echo $lnk.Description = 'Hotel Compare'
echo $lnk.IconLocation = 'shell32.dll,175'
echo $lnk.Save(^)
) > "!PS_SCRIPT!"

powershell -NoProfile -ExecutionPolicy Bypass -File "!PS_SCRIPT!" 2>&1
del "!PS_SCRIPT!" 2>nul

if exist "%USERPROFILE%\Desktop\Hotel Compare.lnk" (
    echo  [OK] Desktop shortcut created
    call :LOG "Shortcut OK"
) else (
    echo  [X] Failed
    call :LOG "Shortcut failed"
)
echo(
pause
goto :MENU

:VIEW_LOG
cls
echo(
echo  =============================================
echo    Logs
echo  =============================================
echo(
echo  [1] Launcher log
echo  [2] Service log
echo  [0] Back
echo(
set "LOG_CHOICE="
set /p "LOG_CHOICE=  Select: "

if "!LOG_CHOICE!"=="1" (
    if exist "!LOGFILE!" (
        cls
        echo(
        echo  --- launcher_log.txt ---
        echo(
        type "!LOGFILE!"
        echo(
    ) else (
        echo  (no log yet)
    )
    echo(
    pause
)
if "!LOG_CHOICE!"=="2" (
    if exist "!INSTALL_DIR!\service_log.txt" (
        cls
        echo(
        echo  --- service_log.txt ---
        echo(
        type "!INSTALL_DIR!\service_log.txt"
        echo(
    ) else (
        echo  (service not started yet)
    )
    echo(
    pause
)
goto :MENU

:UNINSTALL
echo(
call :LOG "=== UNINSTALL ==="
echo  =============================================
echo    Uninstall Hotel Compare
echo  =============================================
echo(
echo    Will delete:
echo      - !INSTALL_DIR!
echo      - Desktop shortcut
echo      - Cookie data
echo(
echo    Chrome profile KEPT.
echo(

set "CONFIRM="
set /p "CONFIRM=  Type YES: "
if not "!CONFIRM!"=="YES" (
    echo  Cancelled.
    timeout /t 1 /nobreak >nul
    goto :MENU
)

echo(
echo  [1/4] Stopping...
call :STOP_SILENT >nul 2>&1
echo  [OK]

echo  [2/4] Shortcut...
del "%USERPROFILE%\Desktop\Hotel Compare.lnk" 2>nul
echo  [OK]

echo  [3/4] Cookies...
rd /s /q "%USERPROFILE%\.hotel-compare\cookies" 2>nul
echo  [OK]

echo  [4/4] Files...
cd /d "%TEMP%"
timeout /t 2 /nobreak >nul
rd /s /q "!INSTALL_DIR!" 2>nul
if exist "!INSTALL_DIR!" (
    echo  [!] Some files locked. Close windows, delete:
    echo      !INSTALL_DIR!
) else (
    echo  [OK]
)

echo(
echo  Done!
echo(
pause
exit /b 0

:EXIT
call :LOG "Exit"
exit /b 0

:: ============================================
:CHECK_PORT
set "FOUND_PID="
set "_NS=%TEMP%\hc_ns_%RANDOM%.txt"
netstat -ano > "!_NS!" 2>nul
for /f "tokens=5" %%p in ('findstr /c:":8888 " "!_NS!" ^| findstr /c:"LISTENING"') do (
    if not "%%p"=="" set "FOUND_PID=%%p"
)
del "!_NS!" 2>nul
goto :eof

:LOG
echo [%date% %time%] %~1 >> "!LOGFILE!"
goto :eof
