"""Small cross-platform helpers (no heavy imports — safe to import anywhere)."""

import os
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

APP_USER_MODEL_ID = "com.kstudy.larksync"


def resource_path(relative: str) -> Path:
    """
    Locate a bundled resource in dev mode, a py2app bundle or a PyInstaller build.
    """
    # PyInstaller (onedir/onefile)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / relative
    # py2app sets RESOURCEPATH to <App>.app/Contents/Resources
    res = os.environ.get("RESOURCEPATH")
    if res:
        return Path(res) / relative
    return Path(__file__).resolve().parent.parent / relative


def set_windows_app_id() -> None:
    """
    Give the process its own taskbar / notification identity so Windows shows
    "LarkSync" (and its icon) on toast notifications instead of "python".
    """
    if not IS_WIN:
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def tray_location_hint() -> str:
    return "menu bar (top-right of your screen)" if IS_MAC else "system tray (near the clock — click ^ if hidden)"
