@echo off
echo ===================================================
echo   Building LarkSync for Windows (Portable .exe)
echo ===================================================
echo.

:: Install PyInstaller if not present
python -m pip install pyinstaller >nul 2>&1

:: Clean old builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist LarkSync.spec del /q LarkSync.spec

echo Building portable .exe...
python build_windows.py

echo.
echo ===================================================
echo   Build Complete!
echo   Output: dist\LarkSync.exe
echo.
echo   This is a portable file - just copy and run!
echo ===================================================
pause
