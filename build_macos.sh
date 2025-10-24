#!/bin/bash
# ========================================
# macOS 打包脚本
# ========================================
# 
# 使用说明:
# 1. 在macOS系统上安装Python 3.10+
# 2. 安装依赖: pip3 install -r requirements.txt
# 3. 安装PyInstaller: pip3 install pyinstaller
# 4. 给脚本添加执行权限: chmod +x build_macos.sh
# 5. 运行此脚本: ./build_macos.sh
# 
# ========================================

set -e  # 遇到错误立即退出

echo "========================================"
echo "Thoracic Database v2.1 - macOS Build"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found! Please install Python 3.10+ first."
    exit 1
fi

echo "[1/5] Checking Python version..."
python3 --version

# 检查依赖
echo "[2/5] Checking dependencies..."
if ! pip3 show openpyxl &> /dev/null; then
    echo "[INFO] Installing dependencies..."
    pip3 install -r requirements.txt
fi

# 检查PyInstaller
echo "[3/5] Checking PyInstaller..."
if ! pip3 show pyinstaller &> /dev/null; then
    echo "[INFO] Installing PyInstaller..."
    pip3 install pyinstaller
fi

# 清理旧的构建文件
echo "[4/5] Cleaning old build files..."
rm -rf build dist

# 开始打包
echo "[5/5] Building macOS application..."
pyinstaller --clean \
    --onefile \
    --windowed \
    --name ThoracicDatabase \
    --icon=assets/app.ico \
    --add-data "db:db" \
    --add-data "ui:ui" \
    --add-data "export:export" \
    --add-data "utils:utils" \
    --add-data "staging:staging" \
    --add-data "assets:assets" \
    --add-data "README.md:." \
    --add-data "CHANGELOG_v2.1.md:." \
    --add-data "VERSION.txt:." \
    --hidden-import=tkinter \
    --hidden-import=tkinter.ttk \
    --hidden-import=tkinter.messagebox \
    --hidden-import=tkinter.filedialog \
    --hidden-import=sqlite3 \
    --hidden-import=openpyxl \
    --hidden-import=openpyxl.styles \
    --hidden-import=openpyxl.utils \
    main.py

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo ""
echo "Application location: dist/ThoracicDatabase"
echo "File size:"
ls -lh dist/ThoracicDatabase | awk '{print $5, $9}'
echo ""
echo "You can now distribute the application to users."
echo "Users do NOT need to install Python to run it."
echo ""
echo "Note: On macOS, users may need to allow the app in"
echo "System Preferences > Security & Privacy"
echo ""

