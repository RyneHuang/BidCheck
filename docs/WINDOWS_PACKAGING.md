# BidCheck Windows 打包指南

本文档说明如何将 BidCheck 打包成 Windows 免安装可执行程序。

## 系统要求

- Windows 10/11 (64位)
- Python 3.10+ (仅打包时需要)
- Node.js 18+ (仅打包时需要，用于构建前端)

## 快速打包

### 方法一：自动打包脚本（推荐）

1. 打开命令提示符，进入项目目录
2. 运行打包脚本：
   ```batch
   scripts\build.bat
   ```
3. 按提示选择打包模式（GUI 或命令行）
4. 完成后在 `dist` 目录找到 `BidCheck.exe`

### 方法二：手动打包

#### 1. 安装依赖

```batch
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装项目依赖
pip install -e .

# 安装打包工具
pip install pyinstaller
```

#### 2. 构建前端

```batch
cd web
npm install
npm run build
cd ..
```

#### 3. 打包

**GUI 版本（推荐）：**
```batch
pyinstaller --clean --noconfirm ^
    --name BidCheck ^
    --onefile ^
    --windowed ^
    --add-data "web/dist;web/dist" ^
    --hidden-import tkinter ^
    --hidden-import docx ^
    --hidden-import openpyxl ^
    --hidden-import pypdf ^
    --hidden-import olefile ^
    --hidden-import fastapi ^
    --hidden-import uvicorn ^
    src/bidcheck/gui_launcher.py
```

**命令行版本：**
```batch
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
    src/bidcheck/cli/main.py
```

## 使用方法

### GUI 版本

1. 双击 `BidCheck.exe`
2. 点击"启动检测系统"按钮
3. 浏览器会自动打开操作界面
4. 上传投标文件进行分析

### 命令行版本

```batch
# 显示帮助
BidCheck.exe --help

# 分析文件
BidCheck.exe analyze 项目名称 投标方A 文件夹A 投标方B 文件夹B

# 启动 Web 服务
BidCheck.exe serve
```

## 分发说明

打包完成后，`dist/BidCheck.exe` 是一个独立的可执行文件，可以：

1. **直接分发** - 复制到任何 Windows 电脑即可运行
2. **创建安装包** - 使用 Inno Setup 或 NSIS 创建安装程序
3. **压缩分发** - 打包成 ZIP 文件

### 文件大小

- GUI 版本：约 50-80 MB
- 命令行版本：约 40-60 MB

### 首次运行

首次运行可能需要 5-10 秒启动时间，这是 PyInstaller 解压临时文件所需的时间。后续运行会更快。

## 常见问题

### Q: 打包时提示找不到模块

A: 确保 `pip install -e .` 成功执行，检查 `pyproject.toml` 中的依赖配置。

### Q: 运行时提示缺少 DLL

A: 安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)。

### Q: 前端无法访问

A: 确保 `web/dist` 目录存在并包含 `index.html`。

### Q: 杀毒软件报毒

A: PyInstaller 打包的程序可能被误报。解决方法：
1. 添加到杀毒软件白名单
2. 使用代码签名证书签名程序
3. 上传到 VirusTotal 获取信任

## 高级选项

### 添加程序图标

1. 准备 `.ico` 格式图标文件
2. 在打包命令中添加 `--icon=icon.ico`

### 减小文件大小

```batch
# 使用 UPX 压缩
pip install pyinstaller[encryption]

pyinstaller --upx-dir=upx ...
```

### 单目录模式（启动更快）

将 `--onefile` 改为 `--onedir`，生成目录而非单文件。

## 技术细节

- 打包工具：PyInstaller 6.x
- Python 版本：3.10+
- 目标平台：Windows 10/11 x64
- 包含依赖：python-docx, openpyxl, pypdf, olefile, FastAPI, Uvicorn

---

如有问题，请访问：https://github.com/RyneHuang/BidCheck/issues
