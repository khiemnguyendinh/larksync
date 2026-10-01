@echo off
setlocal
cd /d "%~dp0"

echo Building LarkSync for Windows...
python -m pip install --quiet -r requirements_windows.txt || goto :error

if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

python build_windows.py || goto :error

echo.
echo Build complete. Outputs in dist\ :
echo   LarkSync\LarkSync.exe              (folder build; also zipped as LarkSync-^<version^>-Windows.zip)
echo   LarkSync-^<version^>-Portable.exe    (single file, no install needed)
echo (python build_windows.py --onedir / --onefile builds just one of them)
echo Optional installer: install Inno Setup 6, then run
echo   iscc /DMyAppVersion=VERSION installer\windows\LarkSync.iss
exit /b 0

:error
echo.
echo Build FAILED.
exit /b 1
