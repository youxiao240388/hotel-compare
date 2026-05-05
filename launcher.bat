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
where chrome >nul 2>&1 && call :LOG "Chrome: found on PATH" || (
    if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
        call :LOG "Chrome: C:\Program Files\Google\Chrome\Application\chrome.exe"
    ) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
        call :LOG "Chrome: %LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
    ) else (
        call :LOG "Chrome: NOT FOUND"
    )
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

:: Check if service is running on port 8888
set "SERVICE_STATUS=Stopped"
set "PID="
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    set "PID=%%p"
    set "SERVICE_STATUS=Running"
)

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
echo    [7] Uninstall (remove everything)
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

:: Check if already running
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    echo  [!] Service already running on port 8888 (PID %%p)
    call :LOG "Already running on 8888 (PID %%p)"
    echo(
    pause
    goto :MENU
)

:: Find Python
set "PY_CMD="
if exist "!INSTALL_DIR!\venv\Scripts\python.exe" (
    set "PY_CMD=!INSTALL_DIR!\venv\Scripts\python.exe"
    call :LOG "Python: venv (!PY_CMD!)"
    goto :FOUND_PY
)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
    call :LOG "Python: system python"
    goto :FOUND_PY
)
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3"
    call :LOG "Python: py -3 launcher"
    goto :FOUND_PY
)

echo  [X] Python not found
call :LOG "ERROR: Python not found"
echo      Install Python: https://apps.microsoft.com/detail/9P7QFQMJRFP7
echo(
pause
goto :MENU

:FOUND_PY
echo  [*] Using: !PY_CMD!
echo  [*] Launching web service...
call :LOG "Launching: !PY_CMD! main.py --web"

:: Start Flask in a new CMD window
start "HotelCompareWeb" cmd /c "cd /d "!INSTALL_DIR!" && "!PY_CMD!" main.py --web 2^> "!INSTALL_DIR!\service_log.txt" & echo. & echo Service stopped. Press any key... & pause >nul"
call :LOG "Service window started"

:: Wait for port 8888
echo  [*] Waiting for service...
set /a "WAIT_COUNT=0"
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a "WAIT_COUNT+=1"
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    echo  [OK] Service started on port 8888
    call :LOG "Service up after !WAIT_COUNT!s (PID %%p)"
    timeout /t 1 /nobreak >nul
    start "" "http://127.0.0.1:8888"
    goto :MENU
)
if !WAIT_COUNT! geq 20 (
    echo  [!] Timeout (20s). Check service_log.txt for errors.
    call :LOG "ERROR: Timeout after 20s waiting for port 8888"
    echo(
    pause
    goto :MENU
)
goto :WAIT_LOOP

:STOP
echo(
call :LOG "=== STOP SERVICE ==="
set "KILLED=0"
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    call :LOG "Killing PID %%p"
    taskkill /pid %%p /f >nul 2>&1
    set "KILLED=1"
)
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
if "!KILLED!"=="1" (
    echo  [OK] Service stopped
    call :LOG "Service stopped"
) else (
    echo  [!] No running service found on port 8888
    call :LOG "No service found on 8888"
)
echo(
pause
goto :MENU

:RESTART
call :LOG "=== RESTART SERVICE ==="
call :STOP_SILENT
echo  [*] Restarting...
timeout /t 2 /nobreak >nul
goto :START

:STOP_SILENT
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    taskkill /pid %%p /f >nul 2>&1
)
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
goto :eof

:OPEN_UI
start "" "http://127.0.0.1:8888"
call :LOG "Opened browser to http://127.0.0.1:8888"
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
echo $lnk.TargetPath = [System.IO.Path]::Combine('!INSTALL_DIR!', 'launcher.bat'^)
echo $lnk.WorkingDirectory = '!INSTALL_DIR!'
echo $lnk.Description = 'Hotel Compare - Service Manager'
echo $lnk.IconLocation = 'shell32.dll,175'
echo $lnk.Save(^)
) > "!PS_SCRIPT!"

powershell -NoProfile -ExecutionPolicy Bypass -File "!PS_SCRIPT!" 2>&1
del "!PS_SCRIPT!" 2>nul

if exist "%USERPROFILE%\Desktop\Hotel Compare.lnk" (
    echo  [OK] Shortcut created on desktop
    call :LOG "Shortcut created"
) else (
    echo  [X] Failed to create shortcut
    call :LOG "ERROR: Shortcut creation failed"
)
echo(
pause
goto :MENU

:VIEW_LOG
cls
echo(
echo  =============================================
echo    Runtime Logs
echo  =============================================
echo(
echo  Launcher log: !LOGFILE!
echo  Service log:  !INSTALL_DIR!\service_log.txt
echo(
echo  --- Last 40 lines of launcher log ---
echo(
if exist "!LOGFILE!" (
    powershell -NoProfile -Command "Get-Content '!LOGFILE!' -Tail 40"
) else (
    echo  (no log file yet)
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
echo    WARNING: Uninstall Hotel Compare
echo  =============================================
echo(
echo    This will:
echo      - Stop the service
echo      - Delete !INSTALL_DIR!
echo      - Delete desktop shortcut
echo      - Delete cookie data
echo(
echo    Chrome profile data will be KEPT.
echo(

set "CONFIRM="
set /p "CONFIRM=  Are you sure? (type YES to confirm): "
if not "!CONFIRM!"=="YES" (
    echo  Cancelled.
    call :LOG "Uninstall cancelled"
    timeout /t 1 /nobreak >nul
    goto :MENU
)

echo(
echo  [1/4] Stopping service...
call :STOP_SILENT >nul 2>&1
echo  [OK] Stopped

echo  [2/4] Removing desktop shortcut...
del "%USERPROFILE%\Desktop\Hotel Compare.lnk" 2>nul
echo  [OK] Removed

echo  [3/4] Removing cookie data...
rd /s /q "%USERPROFILE%\.hotel-compare\cookies" 2>nul
echo  [OK] Removed

echo  [4/4] Removing installation...
call :LOG "Deleting installation directory..."
cd /d "%TEMP%"
timeout /t 2 /nobreak >nul
rd /s /q "!INSTALL_DIR!" 2>nul
if exist "!INSTALL_DIR!" (
    echo  [!] Some files could not be removed
    echo      Close all related windows and delete manually:
    echo      !INSTALL_DIR!
) else (
    echo  [OK] Installation removed
)

echo(
echo  =============================================
echo    Uninstall complete!
echo  =============================================
echo(
pause
exit /b 0

:EXIT
call :LOG "Launcher exited"
exit /b 0

:: ============================================
:: LOG FUNCTION
:: ============================================
:LOG
echo [%date% %time%] %~1 >> "!LOGFILE!"
goto :eof
