@echo off
REM Ultimate build script - copies all source files as data
REM This is the most reliable method when collect-submodules fails

echo ============================================
echo Thoracic Entry - ULTIMATE Build Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
pip install pyinstaller openpyxl

echo.
echo [2/5] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo.
echo [3/5] Building with ALL source files included...
pyinstaller --noconfirm --clean ^
  --onefile ^
  --windowed ^
  --name thoracic_entry ^
  --icon=assets/app.ico ^
  --add-data "assets;assets" ^
  --add-data "ui;ui" ^
  --add-data "db;db" ^
  --add-data "utils;utils" ^
  --add-data "staging;staging" ^
  --add-data "export;export" ^
  --hidden-import=ui.patient_tab ^
  --hidden-import=ui.surgery_tab ^
  --hidden-import=ui.path_tab ^
  --hidden-import=ui.mol_tab ^
  --hidden-import=ui.fu_tab ^
  --hidden-import=ui.export_tab ^
  --hidden-import=db.models ^
  --hidden-import=db.migrate ^
  --hidden-import=utils.validators ^
  --hidden-import=staging.lookup ^
  --hidden-import=export.excel ^
  --hidden-import=export.csv ^
  main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed! Check messages above.
    pause
    exit /b 1
)

echo.
echo [4/5] Verifying output...
if exist dist\thoracic_entry.exe (
    echo.
    echo ============================================
    echo SUCCESS!
    echo ============================================
    echo.
    echo Executable: dist\thoracic_entry.exe
    dir dist\thoracic_entry.exe | find "thoracic_entry.exe"
    echo.
    echo [5/5] Testing the executable...
    echo Starting test run (will close automatically)...
    timeout /t 2 >nul
    start /wait dist\thoracic_entry.exe
    echo.
    echo If the program opened without errors, the build is successful!
    echo.
) else (
    echo ERROR: EXE not found in dist folder!
)

echo.
pause

