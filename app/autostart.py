"""
Launch at login.

v1.0.x bugs fixed here:
  * Settings compared the new value with the value it had *just* saved, so the
    OS entry was never created or removed.
  * macOS: the LaunchAgent ran `sys.executable`, which inside a py2app bundle is
    the bare Python interpreter (no app starts); in dev mode it started a REPL.
    It now runs `open -a <LarkSync.app>`.
  * Windows: the Run key pointed at python.exe when running from source.
  * Paths are no longer interpolated into XML / `os.system` shell strings.
"""

import logging
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from app.platform_utils import IS_MAC, IS_WIN

logger = logging.getLogger(__name__)

LAUNCH_AGENT_LABEL = "com.larksync.agent"     # unchanged so v1.0.x agents are replaced, not duplicated
WIN_RUN_KEY        = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_RUN_VALUE      = "LarkSync"
_MAIN_PY           = Path(__file__).resolve().parent.parent / "main.py"


# ── Command resolution ────────────────────────────────────────────────

def app_bundle_path(executable: Optional[str] = None) -> Optional[Path]:
    """Return the enclosing *.app of the running executable (macOS), if any."""
    for parent in Path(executable or sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    return None


def launch_command() -> List[str]:
    """Command line that starts LarkSync the way the user normally starts it."""
    if IS_MAC:
        bundle = app_bundle_path()
        if bundle:
            return ["/usr/bin/open", "-a", str(bundle)]
        return [sys.executable, str(_MAIN_PY)]                  # running from source
    if IS_WIN:
        if getattr(sys, "frozen", False):
            return [sys.executable]                             # PyInstaller LarkSync.exe
        pythonw = Path(sys.executable).with_name("pythonw.exe")   # no console window
        return [str(pythonw if pythonw.exists() else sys.executable), str(_MAIN_PY)]
    return [sys.executable, str(_MAIN_PY)]


# ── macOS ─────────────────────────────────────────────────────────────

def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"


def build_launch_agent_plist(command: List[str]) -> bytes:
    return plistlib.dumps({
        "Label":              LAUNCH_AGENT_LABEL,
        "ProgramArguments":   list(command),
        "RunAtLoad":          True,
        "KeepAlive":          False,
        "LimitLoadToSessionType": "Aqua",
    })


def _launchctl(*args: str) -> None:
    try:
        subprocess.run(["/bin/launchctl", *args], check=False, timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("launchctl %s failed: %s", args, exc)


def _set_enabled_mac(enabled: bool) -> bool:
    plist = launch_agent_path()
    if enabled:
        from sync.paths import write_private
        plist.parent.mkdir(parents=True, exist_ok=True)
        # Writing the plist is enough: launchd loads ~/Library/LaunchAgents at the
        # next login. We deliberately do not `bootstrap` it now — RunAtLoad would
        # start a second copy of the app immediately.
        write_private(plist, build_launch_agent_plist(launch_command()))
        os.chmod(plist, 0o644)
    else:
        _launchctl("bootout", f"gui/{os.getuid()}/{LAUNCH_AGENT_LABEL}")
        plist.unlink(missing_ok=True)
    return True


# ── Windows ───────────────────────────────────────────────────────────

def windows_run_value(command: List[str]) -> str:
    return subprocess.list2cmdline(command)


def _set_enabled_win(enabled: bool) -> bool:
    import winreg
    try:
        # CreateKeyEx, not OpenKey: the Run key does not exist in a fresh profile and
        # OpenKey then fails with WinError 2 (found by CI on a clean Windows account).
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, WIN_RUN_VALUE, 0, winreg.REG_SZ,
                                  windows_run_value(launch_command()))
            else:
                try:
                    winreg.DeleteValue(key, WIN_RUN_VALUE)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        logger.warning("Failed to update Windows startup entry: %s", exc)
        return False


# ── Public API ────────────────────────────────────────────────────────

def set_enabled(enabled: bool) -> bool:
    try:
        if IS_MAC:
            return _set_enabled_mac(enabled)
        if IS_WIN:
            return _set_enabled_win(enabled)
    except Exception as exc:                        # never let a login-item error break Settings
        logger.warning("Launch-at-login change failed: %s", exc)
        return False
    return False                                    # unsupported platform


def is_enabled() -> bool:
    try:
        if IS_MAC:
            return launch_agent_path().exists()
        if IS_WIN:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
                winreg.QueryValueEx(key, WIN_RUN_VALUE)
            return True
    except OSError:
        pass
    return False
