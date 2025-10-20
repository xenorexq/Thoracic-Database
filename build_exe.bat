@echo off
REM Windows batch script to build thoracic_entry.exe
REM Run this script in Windows Command Prompt

echo ============================================
echo Thoracic Entry - Build Script
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.10 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install pyinstaller openpyxl
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist thoracic_entry.spec del /q thoracic_entry.spec

echo.
echo [3/4] Building executable (this may take a few minutes)...
pyinstaller --noconfirm --clean ^
  --onefile ^
  --windowed ^
  --name thoracic_entry ^
  --icon=assets/app.ico ^
  --add-data "assets;assets" ^
  --paths . ^
  --collect-submodules ui ^
  --collect-submodules db ^
  --collect-submodules utils ^
  --collect-submodules staging ^
  --collect-submodules export ^
  main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo [4/4] Checking output...
if exist dist\thoracic_entry.exe (
    echo.
    echo ============================================
    echo SUCCESS! 
    echo ============================================
    echo.
    echo The executable is located at:
    echo   %CD%\dist\thoracic_entry.exe
    echo.
    echo You can now:
    echo   1. Copy dist\thoracic_entry.exe to any Windows computer
    echo   2. Double-click to run (no Python installation needed)
    echo   3. The program will create thoracic.db automatically
    echo.
    echo File size:
    dir dist\thoracic_entry.exe | find "thoracic_entry.exe"
    echo.
) else (
    echo ERROR: thoracic_entry.exe was not created!
    pause
    exit /b 1
)

echo Press any key to exit...
pause >nul

