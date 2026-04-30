@echo off
echo Building LarkSync for Windows...

:: Install required tools if they don't exist
python -m pip install pyinstaller

:: Clean old builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist LarkSync.spec del /q LarkSync.spec

echo Running PyInstaller...
python build_windows.py

echo Build complete! Check the dist folder.
