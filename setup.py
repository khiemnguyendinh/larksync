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

# NOTE: these must be passed as setup(options={"py2app": ...}). v1.0.x unpacked
# them as setup(py2app=...) — an unknown keyword that setuptools silently ignores
# — so NONE of this was ever applied: no bundle id / version / Retina flag in
# Info.plist, no icon, no assets/ in the bundle, no excludes (bundle was ~400 MB).
PY2APP_OPTIONS = {
    "iconfile":    "assets/icon.icns",   # committed; build.sh can regenerate it from a PNG
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
    # Packages that carry data files or C extensions the import scanner misses.
    # (PyQt6 is deliberately NOT listed: py2app's PyQt6 recipe then bundles only
    # the Qt frameworks/plugins that are actually imported.)
    "packages": [
        "googleapiclient",        # + discovery_cache/documents/drive.v3.json (build.sh prunes the rest)
        "google_auth_oauthlib",
        "google_auth_httplib2",
        "httplib2",
        "certifi",                # CA bundle for requests
        "cryptography",           # google-auth imports it; needs cffi's C extension below
        "cffi",
        "app",
        "sync",
    ],
    "includes": [
        "_cffi_backend",          # top-level C extension that py2app does not discover (found by the CI self-test)
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
        # (stdlib modules are intentionally not excluded: the few MB saved are not
        # worth an ImportError in a lazily-imported code path)
    ],
    "frameworks": [],
    "resources":  ["assets"],           # → <App>.app/Contents/Resources/assets
    "argv_emulation": False,
    "strip":          True,
    "optimize":       1,
}

setup(
    name    = APP_NAME,
    version = VERSION,
    app     = APP,
    options = {"py2app": PY2APP_OPTIONS},
)
