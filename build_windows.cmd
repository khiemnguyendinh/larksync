@echo off
setlocal
cd /d "%~dp0"

echo Building LarkSync for Windows...
python -m pip install --quiet -r requirements_windows.txt || goto :error

if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

python build_windows.py || goto :error

echo.
echo Build complete. Output: dist\LarkSync\LarkSync.exe  (+ the .zip next to it)
echo Optional installer: install Inno Setup 6, then run
echo   iscc /DMyAppVersion=VERSION installer\windows\LarkSync.iss
exit /b 0

:error
echo.
echo Build FAILED.
exit /b 1
