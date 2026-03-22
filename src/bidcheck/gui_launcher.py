#!/usr/bin/env python3
"""BidCheck GUI 启动器 - Windows 双击运行版本"""

import os
import sys
import threading
import webbrowser

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
    """延迟打开浏览器"""
    import time
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")

def main_gui():
    """GUI 模式"""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("tkinter 未安装，使用命令行模式")
        main_cli()
        return

    class BidCheckApp:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("BidCheck 围标检测系统")
            self.root.geometry("500x350")
            self.root.resizable(False, False)

            # 居中显示
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() - 500) // 2
            y = (self.root.winfo_screenheight() - 350) // 2
            self.root.geometry(f"+{x}+{y}")

            self.server_running = False
            self.create_widgets()

        def create_widgets(self):
            # 标题区域
            title_frame = ttk.Frame(self.root, padding="30 20 30 10")
            title_frame.pack(fill=tk.X)

            ttk.Label(
                title_frame,
                text="🔍 BidCheck 围标检测系统",
                font=("Microsoft YaHei", 16, "bold")
            ).pack()

            ttk.Label(
                title_frame,
                text="检测投标文件是否来自同一来源",
                font=("Microsoft YaHei", 9)
            ).pack(pady=(5, 0))

            # 按钮区域
            btn_frame = ttk.Frame(self.root, padding="30 20")
            btn_frame.pack(fill=tk.BOTH, expand=True)

            # 启动按钮
            self.start_btn = ttk.Button(
                btn_frame,
                text="🌐 启动检测系统",
                command=self.start_server,
                width=25
            )
            self.start_btn.pack(pady=10)

            # 状态
            self.status_var = tk.StringVar(value="点击按钮启动系统")
            ttk.Label(
                btn_frame,
                textvariable=self.status_var,
                font=("Microsoft YaHei", 9)
            ).pack(pady=5)

            # 使用说明
            info_frame = ttk.LabelFrame(self.root, text=" 使用说明 ", padding="10")
            info_frame.pack(fill=tk.X, padx=30, pady=10)

            info = "1. 点击上方按钮启动系统\n2. 浏览器会自动打开操作界面\n3. 上传投标文件进行分析"
            ttk.Label(info_frame, text=info, font=("Microsoft YaHei", 9), justify=tk.LEFT).pack()

        def start_server(self):
            if self.server_running:
                messagebox.showinfo("提示", "系统已在运行中\n\n访问地址: http://127.0.0.1:8000")
                return

            self.status_var.set("正在启动...")
            self.start_btn.config(state=tk.DISABLED)

            # 启动服务器
            thread = threading.Thread(target=self._run_server, daemon=True)
            thread.start()

            # 打开浏览器
            threading.Thread(target=open_browser, daemon=True).start()

            self.root.after(3000, lambda: self.status_var.set("运行中 - http://127.0.0.1:8000"))
            self.server_running = True

        def _run_server(self):
            try:
                start_api_server()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"启动失败:\n{e}"))
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

        def run(self):
            self.root.mainloop()

    app = BidCheckApp()
    app.run()

def main_cli():
    """命令行模式"""
    print("=" * 50)
    print("  BidCheck 围标检测系统")
    print("=" * 50)
    print("\n启动 Web 服务器...")
    print("访问地址: http://127.0.0.1:8000")
    print("\n按 Ctrl+C 停止服务器")
    print("-" * 50)

    # 打开浏览器
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动服务器
    start_api_server()

def main():
    """主入口"""
    # 优先使用 GUI 模式
    try:
        main_gui()
    except Exception as e:
        print(f"GUI 模式失败: {e}")
        print("切换到命令行模式...")
        main_cli()

if __name__ == "__main__":
    main()
