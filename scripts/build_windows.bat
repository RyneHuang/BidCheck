@echo off
chcp 65001 >nul
echo ============================================
echo BidCheck Windows 打包工具
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] 检测 Python 环境...
python --version

REM 创建虚拟环境
if not exist "venv_build" (
    echo [2/5] 创建虚拟环境...
    python -m venv venv_build
)

REM 激活虚拟环境
echo [3/5] 激活虚拟环境...
call venv_build\Scripts\activate.bat

REM 安装依赖
echo [4/5] 安装依赖...
pip install --upgrade pip
pip install pyinstaller
pip install -e .

REM 检查前端是否已构建
if not exist "web\dist" (
    echo [警告] web\dist 目录不存在，请先构建前端
    echo 运行: cd web ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)

REM 运行 PyInstaller
echo [5/5] 开始打包...
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

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo ============================================
echo 打包成功！
echo ============================================
echo.
echo 输出文件: dist\BidCheck.exe
echo.
echo 使用方法:
echo   1. 将 dist\BidCheck.exe 复制到任意目录
echo   2. 双击运行或使用命令行参数
echo.
echo 示例:
echo   BidCheck.exe --help
echo   BidCheck.exe analyze --help
echo   BidCheck.exe analyze 项目名 投标方A 文件夹A 投标方B 文件夹B
echo.

pause
