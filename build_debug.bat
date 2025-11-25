@echo off
chcp 65001 >nul
echo ========================================
echo 构建调试版本（带控制台输出）
echo ========================================
echo.

echo [1/3] 清理旧的构建文件...
if exist build\thoracic_debug rmdir /s /q build\thoracic_debug
if exist dist\thoracic_debug.exe del /q dist\thoracic_debug.exe

echo [2/3] 开始打包调试版本...
pyinstaller thoracic_debug.spec

echo.
echo [3/3] 检查构建结果...
if exist dist\thoracic_debug.exe (
    echo ✅ 调试版本构建成功！
    echo.
    echo 📁 输出位置: dist\thoracic_debug.exe
    echo.
    echo 💡 使用说明:
    echo    1. 运行 dist\thoracic_debug.exe
    echo    2. 查看控制台输出的调试信息
    echo    3. 如果出错，将错误信息发给我
    echo.
) else (
    echo ❌ 构建失败，请检查错误信息
    pause
    exit /b 1
)

pause

