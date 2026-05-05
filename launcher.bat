@echo off
chcp 65001 >nul 2>&1
title Hotel Compare - Service Manager
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "INSTALL_DIR=%~dp0"
if "!INSTALL_DIR:~-1!"=="\" set "INSTALL_DIR=!INSTALL_DIR:~0,-1!"
set "LOGFILE=!INSTALL_DIR!\launcher_log.txt"

:: Init log
echo ======================================== > "!LOGFILE!"
echo Hotel Compare Launcher Log >> "!LOGFILE!"
echo Time: %date% %time% >> "!LOGFILE!"
echo Install: !INSTALL_DIR! >> "!LOGFILE!"
echo ======================================== >> "!LOGFILE!"
echo. >> "!LOGFILE!"

call :LOG "Launcher started"
call :LOG "Install dir: !INSTALL_DIR!"

:: Quick environment check
call :LOG "--- Environment ---"
for /f "delims=" %%v in ('python --version 2^>^&1') do call :LOG "Python: %%v"
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    call :LOG "Chrome: found"
) else (
    call :LOG "Chrome: check manually"
)
call :LOG "---"

:MENU
cls
echo(
echo  =============================================
echo    Hotel Compare - Service Manager
echo  =============================================
echo(
echo    Install: !INSTALL_DIR!
echo(

:: Check service status
set "SERVICE_STATUS=Stopped"
set "PID="
set "NETSTAT_TMP=%TEMP%\hc_ns_%RANDOM%.txt"
netstat -ano > "!NETSTAT_TMP!" 2>nul
for /f "tokens=5" %%p in ('findstr /c:":8888 " "!NETSTAT_TMP!" ^| findstr /c:"LISTENING"') do (
    set "PID=%%p"
    set "SERVICE_STATUS=Running"
)
del "!NETSTAT_TMP!" 2>nul

if "!SERVICE_STATUS!"=="Running" (
    echo    Status:  [RUNNING]  PID: !PID!
    echo    Web UI:  http://127.0.0.1:8888
    call :LOG "Status: RUNNING (PID !PID!)"
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
echo    [6] View Log File
echo    [7] Uninstall
echo(
echo    [0] Exit
echo(
echo  =============================================
echo(

set "CHOICE="
set /p "CHOICE=  Select [0-7]: "
call :LOG "User selected: !CHOICE!"

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
call :LOG "=== START SERVICE ==="

:: Check already running
call :CHECK_PORT
if defined FOUND_PID (
    echo  [!] Already running on port 8888 (PID !FOUND_PID!)
    call :LOG "Already running (PID !FOUND_PID!)"
    echo(
    pause
    goto :MENU
)

:: Find Python
set "PY_CMD="
if exist "!INSTALL_DIR!\venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
    call :LOG "Python: venv"
    goto :FOUND_PY
)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
    call :LOG "Python: system"
    goto :FOUND_PY
)
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3"
    call :LOG "Python: py launcher"
    goto :FOUND_PY
)

echo  [X] Python not found
call :LOG "ERROR: Python not found"
echo      Install: https://apps.microsoft.com/detail/9P7QFQMJRFP7
echo(
pause
goto :MENU

:FOUND_PY
echo  [*] Using: !PY_CMD!
echo  [*] Launching web service...
call :LOG "Launching: !PY_CMD! main.py --web"

:: Write a launcher helper script to avoid quote escaping issues
set "LAUNCH_PS=%TEMP%\hc_launch.ps1"
(
echo $pinfo = New-Object System.Diagnostics.ProcessStartInfo
echo $pinfo.FileName = 'cmd.exe'
echo $pinfo.Arguments = '/c cd /d "!INSTALL_DIR!" ^&^& !PY_CMD! main.py --web ^> "!INSTALL_DIR!\service_log.txt" 2^>^&1'
echo $pinfo.WorkingDirectory = '!INSTALL_DIR!'
echo $pinfo.UseShellExecute = $true
echo $pinfo.CreateNoWindow = $false
echo [System.Diagnostics.Process]::Start($pinfo^)
) > "!LAUNCH_PS!"

powershell -NoProfile -ExecutionPolicy Bypass -File "!LAUNCH_PS!" >nul 2>&1
del "!LAUNCH_PS!" 2>nul
call :LOG "Service process launched"

:: Wait for port
echo  [*] Waiting for service...
set /a "WAIT_COUNT=0"
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a "WAIT_COUNT+=1"

call :CHECK_PORT
if defined FOUND_PID (
    echo  [OK] Service started (PID !FOUND_PID!)
    call :LOG "Service up after !WAIT_COUNT!s (PID !FOUND_PID!)"
    timeout /t 1 /nobreak >nul
    start "" "http://127.0.0.1:8888"
    goto :MENU
)

if !WAIT_COUNT! geq 20 (
    echo  [!] Timeout (20s)
    call :LOG "ERROR: Timeout after 20s"
    echo      Check service_log.txt for errors:
    echo      !INSTALL_DIR!\service_log.txt
    echo(
    if exist "!INSTALL_DIR!\service_log.txt" (
        echo  --- Last 10 lines of service log ---
        powershell -NoProfile -Command "Get-Content '!INSTALL_DIR!\service_log.txt' -Tail 10"
        echo  --- end ---
    )
    echo(
    pause
    goto :MENU
)
goto :WAIT_LOOP

:STOP
echo(
call :LOG "=== STOP SERVICE ==="
set "KILLED=0"

call :CHECK_PORT
if defined FOUND_PID (
    call :LOG "Killing PID !FOUND_PID!"
    taskkill /pid !FOUND_PID! /f >nul 2>&1
    set "KILLED=1"
)
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
if "!KILLED!"=="1" (
    echo  [OK] Service stopped
    call :LOG "Service stopped"
) else (
    echo  [!] No running service found
    call :LOG "No service on 8888"
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
if defined FOUND_PID (
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
call :LOG "Creating desktop shortcut..."
set "PS_SCRIPT=%TEMP%\create_shortcut.ps1"

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
    echo  [OK] Shortcut on desktop
    call :LOG "Shortcut created"
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
echo  Launcher: !LOGFILE!
echo  Service:  !INSTALL_DIR!\service_log.txt
echo(
echo  --- launcher_log.txt (last 40 lines) ---
echo(
if exist "!LOGFILE!" (
    powershell -NoProfile -Command "Get-Content '!LOGFILE!' -Tail 40"
) else (
    echo  (not created yet)
)
echo(
echo  --- service_log.txt (last 20 lines) ---
echo(
if exist "!INSTALL_DIR!\service_log.txt" (
    powershell -NoProfile -Command "Get-Content '!INSTALL_DIR!\service_log.txt' -Tail 20"
) else (
    echo  (service not started yet)
)
echo(
echo  =============================================
echo(
pause
goto :MENU

:UNINSTALL
echo(
call :LOG "=== UNINSTALL ==="
echo  =============================================
echo    Uninstall Hotel Compare
echo  =============================================
echo(
echo    Will delete:
echo      - Service (if running)
echo      - !INSTALL_DIR!
echo      - Desktop shortcut
echo      - Cookie data
echo(
echo    Chrome profile will be KEPT.
echo(

set "CONFIRM="
set /p "CONFIRM=  Type YES to confirm: "
if not "!CONFIRM!"=="YES" (
    echo  Cancelled.
    call :LOG "Uninstall cancelled"
    timeout /t 1 /nobreak >nul
    goto :MENU
)

echo(
echo  [1/4] Stopping service...
call :STOP_SILENT >nul 2>&1
echo  [OK]

echo  [2/4] Removing shortcut...
del "%USERPROFILE%\Desktop\Hotel Compare.lnk" 2>nul
echo  [OK]

echo  [3/4] Removing cookies...
rd /s /q "%USERPROFILE%\.hotel-compare\cookies" 2>nul
echo  [OK]

echo  [4/4] Removing files...
call :LOG "Removing !INSTALL_DIR!"
cd /d "%TEMP%"
timeout /t 2 /nobreak >nul
rd /s /q "!INSTALL_DIR!" 2>nul
if exist "!INSTALL_DIR!" (
    echo  [!] Could not delete all files
    echo      Close related windows, then delete:
    echo      !INSTALL_DIR!
) else (
    echo  [OK] Done
)

echo(
echo  Uninstall complete!
echo(
pause
exit /b 0

:EXIT
call :LOG "Exited"
exit /b 0

:: ============================================
:: CHECK_PORT - sets FOUND_PID if port 8888 is listening
:: ============================================
:CHECK_PORT
set "FOUND_PID="
set "_NS=%TEMP%\hc_ns_%RANDOM%.txt"
netstat -ano > "!_NS!" 2>nul
for /f "tokens=5" %%p in ('findstr /c:":8888 " "!_NS!" ^| findstr /c:"LISTENING"') do (
    set "FOUND_PID=%%p"
)
del "!_NS!" 2>nul
goto :eof

:: ============================================
:: LOG - append to log file
:: ============================================
:LOG
echo [%date% %time%] %~1 >> "!LOGFILE!"
goto :eof
