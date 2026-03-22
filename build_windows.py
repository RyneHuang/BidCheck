#!/usr/bin/env python3
"""
BidCheck Windows 打包脚本
使用 PyInstaller 将项目打包成免依赖的可执行程序
"""

import os
import sys
import shutil
import subprocess

def main():
    print("=" * 60)
    print("BidCheck Windows 打包工具")
    print("=" * 60)
    
    # 检查 PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("请运行: pip install pyinstaller")
        return False
    
    # 创建打包目录
    build_dir = "build_windows"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    
    # 创建 spec 文件内容
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/bidcheck/cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含 web 前端文件
        ('web/dist', 'web/dist'),
    ],
    hiddenimports=[
        'docx',
        'openpyxl',
        'pypdf',
        'olefile',
        'fastapi',
        'uvicorn',
        'rich',
        'typer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BidCheck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标: icon='icon.ico'
)
'''
    
    spec_file = os.path.join(build_dir, "BidCheck.spec")
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ 创建 spec 文件: {spec_file}")
    
    # 运行 PyInstaller
    print("\n开始打包...")
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--distpath', os.path.join(build_dir, 'dist'),
        '--workpath', os.path.join(build_dir, 'build'),
        spec_file
    ]
    
    print(f"执行: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✅ 打包成功!")
        print("=" * 60)
        print(f"\n输出目录: {os.path.join(build_dir, 'dist')}")
        print("可执行文件: BidCheck.exe")
        return True
    else:
        print("\n❌ 打包失败")
        return False

if __name__ == "__main__":
    main()
