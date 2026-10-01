"""
py2app build configuration (macOS)
Run: python3 setup.py py2app        (or simply: bash build.sh)
Output: dist/LarkSync.app
"""

import re
from pathlib import Path

from setuptools import setup

APP        = ["main.py"]
APP_NAME   = "LarkSync"
# Single source of truth: app/version.py (read as text so PyQt is not imported here)
VERSION    = re.search(r'__version__\s*=\s*"([^"]+)"',
                       (Path(__file__).parent / "app" / "version.py").read_text(encoding="utf-8")).group(1)

OPTIONS = {
    "app":      APP,
    "options": {
        "py2app": {
            "name":        APP_NAME,
            "iconfile":    "assets/icon.icns",   # committed; build.sh regenerates it if assets/icon.png is newer
            "plist": {
                "CFBundleName":               APP_NAME,
                "CFBundleDisplayName":        APP_NAME,
                "CFBundleIdentifier":         "com.kstudy.larksync",
                "CFBundleVersion":            VERSION,
                "CFBundleShortVersionString": VERSION,
                "LSMinimumSystemVersion":     "12.0",
                "NSHighResolutionCapable":    True,
                "LSUIElement":                False,  # show in Dock + native menu bar
                "NSHumanReadableCopyright":   "© 2026 Khiem Nguyen Dinh - Kstudy Academy. All rights reserved.",
            },
            "packages": [
                "PyQt6",
                "google",
                "googleapiclient",
                "google_auth_oauthlib",
                "google_auth_httplib2",
                "httplib2",
                "certifi",
                "requests",
                "app",
                "sync",
            ],
            "includes": [
                "PyQt6.QtCore",
                "PyQt6.QtGui",
                "PyQt6.QtWidgets",
                "google.oauth2",
                "google.auth",
                "googleapiclient.discovery",
                "googleapiclient.http",
                "google_auth_oauthlib.flow",
                "google.auth.transport.requests",
            ],
            "excludes": [
                # GUI / media toolkits we don't use
                "tkinter", "_tkinter", "Tkinter",
                "matplotlib", "numpy", "scipy", "PIL", "cv2",
                # Unused Qt modules (heavy)
                "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets",
                "PyQt6.QtWebEngine", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineCore",
                "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuickWidgets",
                "PyQt6.QtBluetooth", "PyQt6.QtNfc", "PyQt6.QtPositioning",
                "PyQt6.QtLocation", "PyQt6.QtSensors",
                "PyQt6.Qt3DCore", "PyQt6.Qt3DRender", "PyQt6.Qt3DInput",
                "PyQt6.Qt3DLogic", "PyQt6.Qt3DExtras", "PyQt6.Qt3DAnimation",
                "PyQt6.QtDesigner", "PyQt6.QtHelp",
                "PyQt6.QtSql", "PyQt6.QtTest",
                "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
                "PyQt6.QtPdf", "PyQt6.QtPdfWidgets",
                "PyQt6.QtCharts", "PyQt6.QtDataVisualization",
                "PyQt6.QtRemoteObjects", "PyQt6.QtSerialPort",
                "PyQt6.QtScxml", "PyQt6.QtStateMachine",
                "PyQt6.QtTextToSpeech", "PyQt6.QtVirtualKeyboard",
                # Unused stdlib
                "unittest", "pydoc", "doctest",
                "xmlrpc", "ftplib", "imaplib", "smtplib", "poplib",
                "antigravity", "turtle", "curses",
                "distutils",
                # NOTE: googleapiclient.discovery_cache must stay — googleapiclient
                # imports it inside build(). build.sh only prunes its huge
                # documents/ folder (keeping drive.v3.json).
            ],
            "frameworks": [],
            "resources":  ["assets"],
            "argv_emulation": False,
            "strip":          True,
            "optimize":       1,
        }
    },
}

setup(
    name    = APP_NAME,
    version = VERSION,
    app     = APP,
    **OPTIONS["options"],
)
