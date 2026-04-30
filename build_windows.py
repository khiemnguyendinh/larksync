import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'main.py',
    '--name=LarkSync',
    '--windowed',
    '--icon=assets/icon.ico',
    '--add-data=assets:assets',
    '--add-data=app:app',
    '--add-data=sync:sync',
    '--hidden-import=PyQt6',
    '--hidden-import=googleapiclient',
    '--hidden-import=google_auth_oauthlib',
    '--hidden-import=requests',
    '--clean',
    '-y'
])
