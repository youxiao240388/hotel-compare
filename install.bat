@echo off
chcp 65001 >nul
title 酒店多平台比价工具 - 安装

echo ============================================
echo   酒店多平台比价工具 v2.0 - Windows 安装
echo ============================================
echo.

:: 检测 Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo [OK] Python 已就绪
echo.

:: 检测 Chrome
set CHROME_FOUND=0
for %%p in (
    "C:\Program Files\Google\Chrome\Application\chrome.exe"
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) do (
    if exist %%p (
        echo [OK] Chrome: %%p
        set CHROME_FOUND=1
    )
)

if %CHROME_FOUND%==0 (
    echo [警告] 未找到 Chrome，请手动安装
    echo   下载地址: https://www.google.com/chrome/
)

echo.
echo [安装] Python 依赖...
cd /d "%~dp0"
pip install -r requirements.txt -q

:: 创建数据目录
if not exist "data\history" mkdir "data\history"
if not exist "data\embeddings" mkdir "data\embeddings"
if not exist "%USERPROFILE%\.hotel-compare\chrome-profile" (
    mkdir "%USERPROFILE%\.hotel-compare\chrome-profile"
)

:: 设置 API Key
if "%DEEPSEEK_API_KEY%"=="" (
    echo.
    echo 请输入 DeepSeek API Key（在 https://platform.deepseek.com 获取）:
    set /p API_KEY=
    if not "!API_KEY!"=="" (
        setx DEEPSEEK_API_KEY "!API_KEY!" >nul
        echo [OK] API Key 已保存
    )
)

echo.
echo ============================================
echo   安装完成！
echo ============================================
echo.
echo 使用方法:
echo   python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --checkout 2024-06-02
echo.
echo 首次使用（登录各平台）:
echo   python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --login
echo.
echo 定时监控:
echo   python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --monitor --interval 6h
echo.
pause
