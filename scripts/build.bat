@echo off
chcp 65001 >nul
title BidCheck Windows 打包工具

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║     BidCheck Windows 打包工具                    ║
echo ║     围标检测系统 - 免安装版本                    ║
echo ╚══════════════════════════════════════════════════╝
echo.

REM 步骤 1: 检查 Python
echo [步骤 1/6] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo.
    echo 请先安装 Python 3.10 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo.

REM 步骤 2: 创建虚拟环境
echo [步骤 2/6] 创建虚拟环境...
if not exist "venv_build" (
    python -m venv vv_build
    echo 创建完成
) else (
    echo 虚拟环境已存在
)
echo.

REM 步骤 3: 激活并安装依赖
echo [步骤 3/6] 安装依赖包...
call venv_build\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install pyinstaller >nul 2>&1
pip install -e . >nul 2>&1
echo 依赖安装完成
echo.

REM 步骤 4: 检查前端
echo [步骤 4/6] 检查前端构建...
if not exist "web\dist\index.html" (
    echo [警告] 前端未构建！
    echo.
    echo 请先构建前端:
    echo   cd web
    echo   npm install
    echo   npm run build
    echo.
    set /p continue="是否继续打包（前端功能将不可用）？(y/n): "
    if /i not "%continue%"=="y" exit /b 1
)
echo.

REM 步骤 5: 选择打包模式
echo [步骤 5/6] 选择打包模式:
echo.
echo   1. GUI 版本 (推荐) - 带图形界面，双击运行
echo   2. 命令行版本 - 控制台程序
echo.
set /p mode="请选择 (1/2): "

if "%mode%"=="1" (
    echo.
    echo 正在打包 GUI 版本...
    pyinstaller --clean --noconfirm ^
        --name BidCheck ^
        --onefile ^
        --windowed ^
        --add-data "web/dist;web/dist" ^
        --hidden-import tkinter ^
        --hidden-import tkinter.ttk ^
        --hidden-import docx ^
        --hidden-import openpyxl ^
        --hidden-import pypdf ^
        --hidden-import olefile ^
        --hidden-import fastapi ^
        --hidden-import uvicorn ^
        --hidden-import rich ^
        --hidden-import typer ^
        src/bidcheck/gui_launcher.py
) else (
    echo.
    echo 正在打包命令行版本...
    pyinstaller --clean --noconfirm ^
        --name BidCheck ^
        --onefile ^
        --console ^
        --add-data "web/dist;web/dist" ^
        --hidden-import docx ^
        --hidden-import openpyxl ^
        --hidden-import pypdf ^
        --hidden-import olefile ^
        --hidden-import fastapi ^
        --hidden-import uvicorn ^
        --hidden-import rich ^
        --hidden-import typer ^
        src/bidcheck/cli/main.py
)

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

REM 步骤 6: 完成
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║              打包成功！                          ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 输出文件: dist\BidCheck.exe
echo.
echo 使用方法:
echo   1. 将 BidCheck.exe 复制到任意目录
echo   2. 双击运行（GUI 版本）
echo   3. 或使用命令行参数（命令行版本）
echo.
echo 首次运行可能需要几秒钟启动时间。
echo.

REM 询问是否打开输出目录
set /p open_dir="是否打开输出目录？(y/n): "
if /i "%open_dir%"=="y" explorer dist

pause
