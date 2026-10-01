import plistlib
import sys
from pathlib import Path

from app import autostart


def test_app_bundle_path_found_from_executable():
    exe = "/Applications/LarkSync.app/Contents/MacOS/LarkSync"
    # resolve() on a non-existent path keeps it as-is on POSIX
    assert autostart.app_bundle_path(exe).name == "LarkSync.app"
    assert autostart.app_bundle_path("/usr/bin/python3") is None


def test_launch_agent_plist_runs_open_on_the_bundle():
    cmd = ["/usr/bin/open", "-a", "/Applications/Lark & Sync.app"]   # '&' used to break the XML
    data = plistlib.loads(autostart.build_launch_agent_plist(cmd))
    assert data["Label"] == "com.larksync.agent"
    assert data["ProgramArguments"] == cmd
    assert data["RunAtLoad"] is True and data["KeepAlive"] is False


def test_launch_command_mac_bundle(monkeypatch):
    monkeypatch.setattr(autostart, "IS_MAC", True)
    monkeypatch.setattr(autostart, "IS_WIN", False)
    monkeypatch.setattr(autostart, "app_bundle_path", lambda *a: Path("/Applications/LarkSync.app"))
    # str(Path(...)) because Windows renders the separators as backslashes
    assert autostart.launch_command() == ["/usr/bin/open", "-a", str(Path("/Applications/LarkSync.app"))]


def test_launch_command_from_source_runs_main_py(monkeypatch):
    monkeypatch.setattr(autostart, "IS_MAC", True)
    monkeypatch.setattr(autostart, "IS_WIN", False)
    monkeypatch.setattr(autostart, "app_bundle_path", lambda *a: None)
    cmd = autostart.launch_command()
    assert cmd[0] == sys.executable and cmd[1].endswith("main.py")


def test_launch_command_windows_frozen_and_source(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart, "IS_MAC", False)
    monkeypatch.setattr(autostart, "IS_WIN", True)
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", r"C:\Program Files\LarkSync\LarkSync.exe")
    assert autostart.launch_command() == [r"C:\Program Files\LarkSync\LarkSync.exe"]

    monkeypatch.setattr(autostart.sys, "frozen", False, raising=False)
    (tmp_path / "pythonw.exe").write_text("")
    monkeypatch.setattr(autostart.sys, "executable", str(tmp_path / "python.exe"))
    cmd = autostart.launch_command()
    assert cmd[0].endswith("pythonw.exe") and cmd[1].endswith("main.py")


def test_windows_run_value_quotes_paths_with_spaces():
    value = autostart.windows_run_value([r"C:\Program Files\LarkSync\LarkSync.exe"])
    assert value == '"C:\\Program Files\\LarkSync\\LarkSync.exe"'


def test_enable_disable_launch_agent(monkeypatch, tmp_path):
    monkeypatch.setattr(autostart, "IS_MAC", True)
    monkeypatch.setattr(autostart, "IS_WIN", False)
    monkeypatch.setattr(autostart, "launch_agent_path", lambda: tmp_path / "LaunchAgents" / "x.plist")
    monkeypatch.setattr(autostart, "launch_command", lambda: ["/usr/bin/open", "-a", "/Applications/LarkSync.app"])
    calls = []
    monkeypatch.setattr(autostart, "_launchctl", lambda *a: calls.append(a))
    monkeypatch.setattr(autostart.os, "getuid", lambda: 501, raising=False)

    assert autostart.set_enabled(True) is True
    assert autostart.is_enabled() is True
    assert calls == []                                   # must not bootstrap now (would start a 2nd copy)

    assert autostart.set_enabled(False) is True
    assert autostart.is_enabled() is False
    assert calls == [("bootout", "gui/501/com.larksync.agent")]


def test_settings_apply_launch_at_login_regression(qapp, monkeypatch):
    """v1.0.x compared the new value with the value it had just saved, so this never ran."""
    from app.config_manager import ConfigManager
    from app.settings_dialog import SettingsDialog

    applied = []
    cfg = ConfigManager()
    monkeypatch.setattr(ConfigManager, "set_launch_at_login",
                        lambda self, v: applied.append(v) or True)
    dlg = SettingsDialog(cfg)
    dlg._launch_cb.setChecked(True)
    dlg._apply_updates(dlg._collect_updates())
    assert applied == [True]
