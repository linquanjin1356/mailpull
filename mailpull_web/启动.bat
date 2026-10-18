@echo off
chcp 65001 >nul
title MailPull Web
cd /d "%~dp0"

echo.
echo  ==============================================
echo    MailPull Web — 接码邮箱收信助手
echo  ==============================================
echo.

set PY=
where python >nul 2>nul && set PY=python
if not defined PY ( where py >nul 2>nul && set PY=py )
if not defined PY (
    echo [错误] 没找到 Python，请先安装并勾选 "Add to PATH"
    echo        https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  正在启动本地服务，稍后会自动打开浏览器...
echo  用完直接关掉这个窗口即可。
echo.

%PY% server.py

pause
