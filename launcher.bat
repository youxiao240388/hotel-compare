@echo off
:: Pure ASCII - no encoding issues
chcp 65001 >nul 2>&1
title Hotel Compare - Service Manager
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "INSTALL_DIR=%~dp0"
:: Remove trailing backslash if present
if "!INSTALL_DIR:~-1!"=="\" set "INSTALL_DIR=!INSTALL_DIR:~0,-1!"

:MENU
cls
echo.
echo  =============================================
echo    Hotel Compare - Service Manager
echo  =============================================
echo.
echo    Install: %INSTALL_DIR%
echo.

:: Check if service is running
set "SERVICE_STATUS=Stopped"
set "PID="
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fi "windowtitle eq HotelCompareWeb*" 2^>nul ^| findstr "python"') do (
    set "PID=%%a"
)
:: Also check by port
netstat -ano 2>nul | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    set "SERVICE_STATUS=Running"
    for /f "tokens=5" %%p in ('netstat -ano 2>nul ^| findstr ":8888" ^| findstr "LISTENING"') do set "PID=%%p"
)

if "!SERVICE_STATUS!"=="Running" (
    echo    Status:  [RUNNING]  PID: !PID!
    echo    Web UI:  http://127.0.0.1:8888
) else (
    echo    Status:  [STOPPED]
)
echo.
echo  =============================================
echo.
echo    [1] Start Service
echo    [2] Stop Service
echo    [3] Restart Service
echo    [4] Open Web UI
echo.
echo    [5] Create Desktop Shortcut
echo    [6] Uninstall (remove everything)
echo.
echo    [0] Exit
echo.
echo  =============================================
echo.

choice /c 1234560 /n /m "  Select [0-6]: "
set "CHOICE=%errorlevel%"

if %CHOICE%==1 goto :START
if %CHOICE%==2 goto :STOP
if %CHOICE%==3 goto :RESTART
if %CHOICE%==4 goto :OPEN_UI
if %CHOICE%==5 goto :SHORTCUT
if %CHOICE%==6 goto :UNINSTALL
if %CHOICE%==7 goto :EOF

goto :MENU

:START
echo.
echo  Starting service...

:: Check if already running
netstat -ano 2>nul | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [!] Service already running on port 8888
    echo.
    pause
    goto :MENU
)

:: Find Python
set "PY_CMD="
if exist "venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
) else (
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=python"
    ) else (
        py -3 --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY_CMD=py -3"
        )
    )
)

if "!PY_CMD!"=="" (
    echo  [X] Python not found
    echo      Install Python from https://apps.microsoft.com/detail/9P7QFQMJRFP7
    pause
    goto :MENU
)

:: Start Flask in a new window
echo  [*] Launching with !PY_CMD!...
start "HotelCompareWeb" /D "%INSTALL_DIR%" cmd /c "!PY_CMD! main.py --web 2>&1 & pause"

:: Wait for port to come up
echo  [*] Waiting for port 8888...
set /a "WAIT=0"
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a "WAIT+=1"
netstat -ano 2>nul | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Service started
    timeout /t 1 /nobreak >nul
    start "" "http://127.0.0.1:8888"
    goto :MENU
)
if !WAIT! geq 15 (
    echo  [!] Timeout waiting for service
    echo      Check the new window for errors
    pause
    goto :MENU
)
goto :WAIT_LOOP

:STOP
echo.
echo  Stopping service...
set "KILLED=0"
for /f "tokens=2,5" %%a in ('netstat -ano 2>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    taskkill /pid %%b /f >nul 2>&1
    set "KILLED=1"
)
:: Also kill any HotelCompareWeb titled windows
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
if "!KILLED!"=="1" (
    echo  [OK] Service stopped
) else (
    echo  [!] No running service found on port 8888
)
echo.
pause
goto :MENU

:RESTART
call :STOP_SILENT
timeout /t 2 /nobreak >nul
goto :START

:STOP_SILENT
for /f "tokens=5" %%p in ('netstat -ano 2>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    taskkill /pid %%p /f >nul 2>&1
)
taskkill /fi "windowtitle eq HotelCompareWeb*" /f >nul 2>&1
goto :eof

:OPEN_UI
start "" "http://127.0.0.1:8888"
echo  [OK] Browser opened
timeout /t 2 /nobreak >nul
goto :MENU

:SHORTCUT
echo.
echo  Creating desktop shortcut...
set "PS_SCRIPT=%TEMP%\create_shortcut.ps1"
(
echo $ws = New-Object -ComObject WScript.Shell
echo $desktop = [Environment]::GetFolderPath('Desktop'^)
echo $lnk = $ws.CreateShortcut("$desktop\Hotel Compare.lnk"^)
echo $lnk.TargetPath = '%INSTALL_DIR%\launcher.bat'
echo $lnk.WorkingDirectory = '%INSTALL_DIR%'
echo $lnk.Description = 'Hotel Compare - Service Manager'
echo $lnk.IconLocation = 'shell32.dll,175'
echo $lnk.Save(^)
echo Write-Host '[OK] Shortcut created on desktop'
) > "%PS_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" 2>&1
del "%PS_SCRIPT%" 2>nul
echo.
pause
goto :MENU

:UNINSTALL
echo.
echo  =============================================
echo    WARNING: Uninstall Hotel Compare
echo  =============================================
echo.
echo    This will:
echo      - Stop the service
echo      - Delete %INSTALL_DIR%
echo      - Delete desktop shortcut
echo      - Delete cookie data
echo.
echo    Your Chrome profile data will be KEPT.
echo.

choice /c YN /n /m "  Are you sure? [Y/N]: "
if %errorlevel% neq 1 goto :MENU

echo.
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
cd /d "%TEMP%"
timeout /t 2 /nobreak >nul
rd /s /q "%INSTALL_DIR%" 2>nul
if exist "%INSTALL_DIR%" (
    echo  [!] Some files could not be removed
    echo      Close all related windows and delete manually:
    echo      %INSTALL_DIR%
) else (
    echo  [OK] Installation removed
)

echo.
echo  =============================================
echo    Uninstall complete!
echo  =============================================
echo.
pause
exit /b 0
