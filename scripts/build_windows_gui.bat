@echo off
chcp 65001 >nul
echo ============================================
echo BidCheck Windows GUI 打包工具
echo ============================================
echo.
echo 此脚本将打包带图形界面的版本
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    pause
    exit /b 1
)

REM 创建 GUI 启动器脚本
echo [1/4] 创建 GUI 启动器...
mkdir -p build_temp 2>nul

cat > build_temp\gui_launcher.py << 'PYEOF'
#!/usr/bin/env python3
"""BidCheck GUI 启动器"""
import os
import sys
import subprocess
import threading
import webbrowser
from pathlib import Path

# 尝试导入 tkinter
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False
    print("警告: tkinter 未安装，使用命令行模式")

def resource_path(relative_path):
    """获取资源文件路径（兼容 PyInstaller）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

def start_api_server():
    """启动 API 服务器"""
    import uvicorn
    from bidcheck.api.main import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def open_browser():
    """打开浏览器"""
    webbrowser.open("http://127.0.0.1:8000")

class BidCheckGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BidCheck 围标检测系统")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        self.server_thread = None
        self.server_running = False

        self.create_widgets()

    def create_widgets(self):
        # 标题
        title_frame = ttk.Frame(self.root, padding="20")
        title_frame.pack(fill=tk.X)

        ttk.Label(
            title_frame,
            text="🔍 BidCheck 围标检测系统",
            font=("Arial", 18, "bold")
        ).pack()

        ttk.Label(
            title_frame,
            text="检测投标文件是否来自同一来源",
            font=("Arial", 10)
        ).pack(pady=(5, 0))

        # 主要按钮区域
        btn_frame = ttk.Frame(self.root, padding="20")
        btn_frame.pack(fill=tk.BOTH, expand=True)

        # 启动 Web 界面按钮
        self.web_btn = ttk.Button(
            btn_frame,
            text="🌐 启动 Web 界面",
            command=self.start_web_interface,
            width=30
        )
        self.web_btn.pack(pady=10)

        # 状态显示
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            btn_frame,
            textvariable=self.status_var,
            font=("Arial", 10)
        )
        status_label.pack(pady=10)

        # 使用说明
        info_frame = ttk.LabelFrame(self.root, text="使用说明", padding="10")
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        info_text = """
1. 点击"启动 Web 界面"按钮
2. 浏览器会自动打开操作界面
3. 上传投标文件进行分析
4. 查看风险评分和检测报告
        """

        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack()

        # 底部信息
        footer = ttk.Frame(self.root)
        footer.pack(fill=tk.X, side=tk.BOTTOM, pady=10)

        ttk.Label(
            footer,
            text="© 2024 BidCheck - 围标检测系统",
            font=("Arial", 8)
        ).pack()

    def start_web_interface(self):
        if self.server_running:
            messagebox.showinfo("提示", "服务器已在运行中\n\n访问地址: http://127.0.0.1:8000")
            return

        self.status_var.set("正在启动服务器...")
        self.web_btn.config(state=tk.DISABLED)

        # 启动服务器线程
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # 延迟打开浏览器
        self.root.after(2000, self._on_server_started)

    def _run_server(self):
        try:
            self.server_running = True
            start_api_server()
        except Exception as e:
            self.server_running = False
            self.root.after(0, lambda: self._on_server_error(str(e)))

    def _on_server_started(self):
        self.status_var.set("服务器运行中 - http://127.0.0.1:8000")
        open_browser()

    def _on_server_error(self, error):
        self.status_var.set("启动失败")
        self.web_btn.config(state=tk.NORMAL)
        messagebox.showerror("错误", f"服务器启动失败:\n{error}")

    def run(self):
        self.root.mainloop()

def main():
    if HAS_TK:
        app = BidCheckGUI()
        app.run()
    else:
        print("=" * 50)
        print("BidCheck 围标检测系统")
        print("=" * 50)
        print("\n启动 Web 服务器...")
        print("访问地址: http://127.0.0.1:8000")
        print("\n按 Ctrl+C 停止服务器")
        print("-" * 50)
        start_api_server()

if __name__ == "__main__":
    main()
PYEOF

echo [2/4] 安装依赖...
if not exist "venv_build" python -m venv venv_build
call venv_build\Scripts\activate.bat
pip install --upgrade pip pyinstaller
pip install -e .

echo [3/4] 检查前端...
if not exist "web\dist" (
    echo [错误] 请先构建前端: cd web ^&^& npm run build
    pause
    exit /b 1
)

echo [4/4] 打包 GUI 版本...
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
    build_temp\gui_launcher.py

echo.
echo ============================================
echo GUI 版本打包完成！
echo ============================================
echo 输出文件: dist\BidCheck.exe
echo.

pause
