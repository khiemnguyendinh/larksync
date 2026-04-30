"""
py2app build configuration
Run: python3 setup.py py2app
Output: dist/LarkSync.app
"""

from setuptools import setup

APP        = ["main.py"]
APP_NAME   = "LarkSync"
VERSION    = "1.0.0"

OPTIONS = {
    "app":      APP,
    "options": {
        "py2app": {
            "name":        APP_NAME,
            "iconfile":    "assets/icon.icns",   # see build.sh for icon generation
            "plist": {
                "CFBundleName":               APP_NAME,
                "CFBundleDisplayName":        APP_NAME,
                "CFBundleIdentifier":         "com.kstudy.larksync",
                "CFBundleVersion":            VERSION,
                "CFBundleShortVersionString": VERSION,
                "NSHighResolutionCapable":    True,
                "LSUIElement":                False,  # show in Dock + native menu bar
                "NSHumanReadableCopyright":   "© 2026 Kstudy Academy",
            },
            "packages": [
                "PyQt6",
                "google",
                "googleapiclient",
                "google_auth_oauthlib",
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
                # Google APIs we don't use (shrinks discovery_cache usage)
                "googleapiclient.discovery_cache",
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
