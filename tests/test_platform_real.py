"""
Tests that touch the real OS integration. Each only runs on its own platform
(CI runs the suite on Linux, macOS and Windows).
"""
import plistlib
import subprocess
import sys

import pytest

from app import autostart


@pytest.mark.skipif(sys.platform != "win32", reason="Windows registry")
def test_windows_run_key_roundtrip():
    import winreg
    try:
        assert autostart.set_enabled(True) is True
        assert autostart.is_enabled() is True
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart.WIN_RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, autostart.WIN_RUN_VALUE)
        assert value == autostart.windows_run_value(autostart.launch_command())
        assert autostart.set_enabled(False) is True
        assert autostart.is_enabled() is False
    finally:
        autostart.set_enabled(False)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows tray behaviour")
def test_windows_app_user_model_id_can_be_set():
    from app.platform_utils import set_windows_app_id
    set_windows_app_id()                          # must never raise


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS LaunchAgent")
def test_macos_launch_agent_is_valid_and_removed(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(autostart, "_launchctl", lambda *a: None)
    try:
        assert autostart.set_enabled(True) is True
        plist = autostart.launch_agent_path()
        assert plist.exists() and tmp_path in plist.parents
        assert plistlib.loads(plist.read_bytes())["Label"] == "com.larksync.agent"
        lint = subprocess.run(["/usr/bin/plutil", "-lint", str(plist)], capture_output=True, text=True)
        assert lint.returncode == 0, lint.stdout + lint.stderr
        assert autostart.set_enabled(False) is True
        assert not plist.exists()
    finally:
        autostart.set_enabled(False)


def test_data_dir_matches_the_platform():
    """Run without LARKSYNC_HOME to see the real default for this OS."""
    import os
    from sync import paths
    saved = os.environ.pop("LARKSYNC_HOME", None)
    try:
        resolved = paths._resolve_app_dir()
    finally:
        if saved is not None:
            os.environ["LARKSYNC_HOME"] = saved
    assert resolved.name == "LarkSync" and "Documents" not in resolved.parts
    if sys.platform == "darwin":
        assert resolved.parts[-3:] == ("Library", "Application Support", "LarkSync")
    elif sys.platform == "win32":
        assert "AppData" in resolved.parts or "APPDATA" in os.environ
