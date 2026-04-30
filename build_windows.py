"""
Build LarkSync for Windows — Portable single-file .exe
Usage: python build_windows.py [--onedir]

Default: builds a single portable .exe (--onefile)
With --onedir: builds a folder-based distribution (faster startup)
"""

import PyInstaller.__main__
import os
import sys


def build(onefile=True):
    icon_arg = []
    if os.path.exists('assets/icon.ico'):
        icon_arg = ['--icon=assets/icon.ico']

    mode = '--onefile' if onefile else '--onedir'
    label = 'portable' if onefile else 'full'
    print(f"\n{'='*50}")
    print(f"  Building LarkSync ({label}) with {mode}")
    print(f"{'='*50}\n")

    PyInstaller.__main__.run([
        'main.py',
        '--name=LarkSync',
        mode,
        '--windowed',
        *icon_arg,
        '--add-data=assets;assets',
        '--hidden-import=PyQt6',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=google.oauth2',
        '--hidden-import=google.auth',
        '--hidden-import=google.auth.transport.requests',
        '--hidden-import=googleapiclient.discovery',
        '--hidden-import=googleapiclient.http',
        '--hidden-import=google_auth_oauthlib.flow',
        '--hidden-import=requests',
        '--hidden-import=app',
        '--hidden-import=app.config_manager',
        '--hidden-import=app.setup_wizard',
        '--hidden-import=app.tray_app',
        '--hidden-import=app.settings_dialog',
        '--hidden-import=app.log_viewer',
        '--hidden-import=app.sync_thread',
        '--hidden-import=app.win_menu',
        '--hidden-import=sync',
        '--hidden-import=sync.lark_auth',
        '--hidden-import=sync.lark_client',
        '--hidden-import=sync.google_client',
        '--hidden-import=sync.sync_engine',
        '--hidden-import=sync.lark_notifier',
        '--collect-submodules=app',
        '--collect-submodules=sync',
        '--clean',
        '-y',
    ])

    if onefile:
        print(f"\n✓ Portable .exe built: dist/LarkSync.exe")
        print(f"  Copy this single file anywhere and run it!")
    else:
        print(f"\n✓ Full distribution built: dist/LarkSync/LarkSync.exe")
        print(f"  Distribute the entire dist/LarkSync/ folder.")


if __name__ == '__main__':
    onedir = '--onedir' in sys.argv
    build(onefile=not onedir)
