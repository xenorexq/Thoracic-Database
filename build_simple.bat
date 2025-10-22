@echo off
echo ============================================
echo Thoracic Entry - Simple Build
echo ============================================
echo.

echo Installing dependencies...
pip install -q pyinstaller openpyxl

echo.
echo Cleaning...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building (this takes 1-2 minutes)...
pyinstaller --clean thoracic_ultimate.spec

echo.
if exist dist\thoracic_entry.exe (
    echo SUCCESS! EXE created at: dist\thoracic_entry.exe
    dir dist\thoracic_entry.exe
) else (
    echo FAILED! Check error messages above.
)

echo.
pause

