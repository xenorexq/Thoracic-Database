# -*- coding: utf-8 -*-
"""
调试版本的启动脚本 - 用于诊断EXE打包问题
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

print("=" * 60)
print("调试信息 - 启动前")
print("=" * 60)
print(f"Python版本: {sys.version}")
print(f"当前工作目录: {os.getcwd()}")
print(f"sys.executable: {sys.executable}")
print(f"sys.frozen: {getattr(sys, 'frozen', False)}")
print(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
print(f"__file__: {__file__}")
print("=" * 60)

# 检查关键模块
print("\n检查关键模块导入...")
try:
    import tkinter as tk
    print("✅ tkinter")
except Exception as e:
    print(f"❌ tkinter: {e}")
    sys.exit(1)

try:
    import ttkbootstrap as tb
    print("✅ ttkbootstrap")
except Exception as e:
    print(f"❌ ttkbootstrap: {e}")
    print("⚠️ 将回退到标准tkinter")

try:
    import sqlite3
    print("✅ sqlite3")
except Exception as e:
    print(f"❌ sqlite3: {e}")
    sys.exit(1)

try:
    import openpyxl
    print("✅ openpyxl")
except Exception as e:
    print(f"❌ openpyxl: {e}")

print("\n检查项目模块...")
try:
    from db.models import Database, DEFAULT_DB_PATH
    print(f"✅ db.models")
    print(f"   DEFAULT_DB_PATH: {DEFAULT_DB_PATH}")
except Exception as e:
    print(f"❌ db.models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from ui.patient_tab import PatientTab
    print("✅ ui.patient_tab")
except Exception as e:
    print(f"❌ ui.patient_tab: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n检查assets目录...")
if getattr(sys, 'frozen', False):
    assets_dir = Path(sys._MEIPASS) / "assets"
else:
    assets_dir = Path(__file__).parent / "assets"

print(f"assets目录: {assets_dir}")
print(f"assets存在: {assets_dir.exists()}")
if assets_dir.exists():
    files = list(assets_dir.glob("*"))
    print(f"assets文件数: {len(files)}")
    for f in files[:5]:
        print(f"  - {f.name}")

print("\n" + "=" * 60)
print("开始启动主程序...")
print("=" * 60 + "\n")

# 导入主程序
try:
    print("\n导入main模块...")
    from main import ThoracicApp
    print("✅ main.ThoracicApp导入成功")
    
    print("\n创建tkinter窗口...")
    import tkinter as tk
    try:
        import ttkbootstrap as tb
        root = tb.Window(themename="cosmo")
        print("✅ 使用ttkbootstrap主题")
    except Exception as e:
        print(f"⚠️ ttkbootstrap失败: {e}")
        print("使用标准tkinter")
        root = tk.Tk()
    
    print("\n初始化ThoracicApp...")
    app = ThoracicApp(root)
    print("✅ ThoracicApp初始化成功")
    
    print("\n启动主循环...")
    root.mainloop()
    
except Exception as e:
    print(f"\n❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    input("\n按回车键退出...")
    sys.exit(1)

