@echo off
chcp 65001 >nul
REM ============================================
REM  MailPull 一键打包成 exe
REM  双击本文件即可生成 dist\MailPull.exe
REM ============================================
title MailPull 打包工具

echo.
echo  ==============================================
echo    MailPull  -  一键打包
echo  ==============================================
echo.

REM 找 python
set PY=
where python >nul 2>nul && set PY=python
if not defined PY (
    where py >nul 2>nul && set PY=py
)
if not defined PY (
    echo [错误] 没找到 Python，请先安装 Python 并勾选 "Add to PATH"
    echo        下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 使用 Python: 
%PY% --version
echo.

echo [2/4] 安装打包依赖 pyinstaller...
%PY% -m pip install pyinstaller -q --upgrade
if errorlevel 1 (
    echo [错误] pyinstaller 安装失败，请检查网络
    pause
    exit /b 1
)
echo       完成
echo.

echo [3/4] 清理旧的构建文件...
if exist build rd /s /q build
if exist dist rd /s /q dist
echo       完成
echo.

echo [4/4] 开始打包...
%PY% -m PyInstaller -F -w --clean --name MailPull mailpull.py
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo  ==============================================
echo    打包完成！
echo.
echo    成品位置: %cd%\dist\MailPull.exe
echo.
echo    把 dist\MailPull.exe 发给客户即可，
echo    客户电脑不需要装 Python，双击直接用。
echo  ==============================================
echo.
pause