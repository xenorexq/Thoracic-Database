@echo off
REM ========================================
REM Windows Build Script
REM Thoracic Database v2.11
REM ========================================
REM 
REM Usage:
REM 1. Install Python 3.10+ on Windows
REM 2. Install dependencies: pip install -r requirements.txt
REM 3. Install PyInstaller: pip install pyinstaller
REM 4. Run this script: build_windows.bat
REM 
REM ========================================

echo ========================================
echo Thoracic Database v2.11 - Windows Build
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+ first.
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Check dependencies
echo [2/5] Checking dependencies...
pip show openpyxl >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
)

REM Check PyInstaller
echo [3/5] Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

REM Clean old build files
echo [4/5] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Start building
echo [5/5] Building Windows executable...
pyinstaller --clean --onefile --windowed --name ThoracicDatabase --icon=assets/app.ico --add-data "db;db" --add-data "ui;ui" --add-data "export;export" --add-data "utils;utils" --add-data "staging;staging" --add-data "assets;assets" --add-data "README.md;." --add-data "CHANGELOG_v2.11.md;." --add-data "VERSION.txt;." --hidden-import=tkinter --hidden-import=tkinter.ttk --hidden-import=tkinter.messagebox --hidden-import=tkinter.filedialog --hidden-import=sqlite3 --hidden-import=openpyxl --hidden-import=openpyxl.styles --hidden-import=openpyxl.utils main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\ThoracicDatabase.exe
echo File size:
dir dist\ThoracicDatabase.exe | find "ThoracicDatabase.exe"
echo.
echo You can now distribute the .exe file to users.
echo Users do NOT need to install Python to run it.
echo.
pause

