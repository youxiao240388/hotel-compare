@echo off
chcp 65001 >nul 2>&1
title Hotel Compare - Environment Check
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "INSTALL_DIR=%~dp0"
if "!INSTALL_DIR:~-1!"=="\" set "INSTALL_DIR=!INSTALL_DIR:~0,-1!"
set "LOGFILE=!INSTALL_DIR!\check_env_log.txt"

echo ======================================== > "!LOGFILE!"
echo Hotel Compare Environment Check >> "!LOGFILE!"
echo Time: %date% %time% >> "!LOGFILE!"
echo ======================================== >> "!LOGFILE!"

echo(
echo  =============================================
echo    Hotel Compare - Environment Check
echo  =============================================
echo(

:: 1. OS
echo  [1/7] Operating System
for /f "tokens=2 delims==" %%a in ('wmic os get Caption /value 2^>nul ^| find "Caption"') do (
    echo       %%a
    echo OS: %%a >> "!LOGFILE!"
)
echo(

:: 2. Python
echo  [2/7] Python
set "PY_OK=0"
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "delims=" %%v in ('python --version 2^>^&1') do (
        echo       [OK] %%v
        echo Python: %%v >> "!LOGFILE!"
    )
    set "PY_OK=1"
) else (
    py -3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "delims=" %%v in ('py -3 --version 2^>^&1') do (
            echo       [OK] %%v (via py launcher)
            echo Python: %%v (py launcher) >> "!LOGFILE!"
        )
        set "PY_OK=1"
    )
)
if "!PY_OK!"=="0" (
    echo       [X] Python NOT FOUND
    echo       Install: https://apps.microsoft.com/detail/9P7QFQMJRFP7
    echo Python: NOT FOUND >> "!LOGFILE!"
)
echo(

:: 3. pip packages
echo  [3/7] Python Packages
if "!PY_OK!"=="1" (
    for %%p in (flask DrissionPage requests beautifulsoup4 lxml) do (
        python -c "import %%p" >nul 2>&1
        if !errorlevel! equ 0 (
            echo       [OK] %%p
            echo Package %%p: OK >> "!LOGFILE!"
        ) else (
            echo       [X] %%p - missing
            echo Package %%p: MISSING >> "!LOGFILE!"
        )
    )
) else (
    echo       [SKIP] Python not available
)
echo(

:: 4. Chrome
echo  [4/7] Chrome Browser
set "CHROME_OK=0"
for %%p in (
    "C:\Program Files\Google\Chrome\Application\chrome.exe"
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) do (
    if exist %%p (
        echo       [OK] %%p
        echo Chrome: %%p >> "!LOGFILE!"
        set "CHROME_OK=1"
    )
)
if "!CHROME_OK!"=="0" (
    echo       [X] Chrome NOT FOUND
    echo       Install: https://www.google.com/chrome/
    echo Chrome: NOT FOUND >> "!LOGFILE!"
)
echo(

:: 5. Project files
echo  [5/7] Project Files
for %%f in (main.py requirements.txt launcher.bat) do (
    if exist "!INSTALL_DIR!\%%f" (
        echo       [OK] %%f
    ) else (
        echo       [X] %%f MISSING
        echo File %%f: MISSING >> "!LOGFILE!"
    )
)
for %%d in (src\platforms src\web src\web\templates) do (
    if exist "!INSTALL_DIR!\%%d" (
        echo       [OK] %%d\
    ) else (
        echo       [X] %%d\ MISSING
        echo Dir %%d: MISSING >> "!LOGFILE!"
    )
)
echo(

:: 6. Port 8888
echo  [6/7] Port 8888
netstat -ano 2>nul | findstr ":8888" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
        echo       [!] Port 8888 in use (PID %%p)
        echo       Stop with: taskkill /pid %%p /f
        echo Port 8888: IN USE (PID %%p) >> "!LOGFILE!"
    )
) else (
    echo       [OK] Port 8888 available
    echo Port 8888: available >> "!LOGFILE!"
)
echo(

:: 7. Chrome profile
echo  [7/7] Chrome Profile Data
if exist "%USERPROFILE%\.hotel-compare\chrome-profile" (
    echo       [OK] %USERPROFILE%\.hotel-compare\chrome-profile
) else (
    echo       [!] Not created yet (will be created on first run)
)
echo(

:: Summary
echo  =============================================
echo    Log saved: !LOGFILE!
echo  =============================================
echo(
pause
