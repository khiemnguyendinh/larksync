# LarkSync for Windows

This guide explains how to build and use LarkSync on Windows.

## Building from source

1. Ensure you have Python installed.
2. Install the requirements:
   ```powershell
   pip install -r requirements_windows.txt
   ```
3. Prepare an icon file named `icon.ico` and place it in the `assets/` directory.
4. Run the build script:
   ```powershell
   .\build_windows.ps1
   ```
5. The executable will be generated in the `dist\LarkSync` folder.

## Running LarkSync

You can run the built executable `LarkSync.exe` directly.
The application will appear in your system tray (the area near the clock on your taskbar).

Features are identical to the macOS version:
- Connect Lark Drive & Google Drive
- Scheduled or manual sync
- System tray integration
- Launch at login

The configuration files will be stored in your `Documents/lark_gdrive_sync` folder.
