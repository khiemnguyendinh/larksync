"""
LarkSync — Entry Point
1. Allow only one running copy of the app
2. Show Setup Wizard on first run
3. Start the tray / menu-bar app (+ native menu bar on macOS)

`main.py --selftest` verifies a packaged build (imports, bundled data, widgets)
and exits 0/1 — used by CI on the macOS .app and the Windows .exe.
"""

import os
import sys
import time
from pathlib import Path

# ── Ensure app/ and sync/ modules are importable ──────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore    import QEvent, QLockFile, QTimer
from PyQt6.QtGui     import QIcon

from app.config_manager import ConfigManager, INSTANCE_LOCK_FILE, APP_DIR
from app.platform_utils import IS_MAC, resource_path, set_windows_app_id, tray_location_hint
from app.setup_wizard   import SetupWizard
from app.tray_app       import TrayApp
from app.version        import __version__, APP_NAME

if IS_MAC:
    from app.mac_menu_bar import build_menu_bar


class LarkSyncApp(QApplication):
    """QApplication subclass — on macOS, clicking the Dock icon re-opens Settings."""

    # Ignore the activation macOS sends while the app is still launching.
    _STARTUP_GRACE_SECONDS = 2.0

    def __init__(self, argv):
        super().__init__(argv)
        self._tray_ref = None   # set after TrayApp is created
        self._started_at = time.monotonic()

    def event(self, event: QEvent) -> bool:
        # ApplicationActivate fires when the app becomes active, e.g. the user clicks
        # the Dock icon (or ⌘-Tabs back) while no LarkSync window is in front.
        # v1.1: macOS only (on Windows it re-opened Settings behind the tray menu's
        # back), goes through the tray's single-dialog guard, skips the launch
        # activation and never opens on top of another dialog.
        if (IS_MAC
                and event.type() == QEvent.Type.ApplicationActivate
                and self._tray_ref is not None
                and time.monotonic() - self._started_at > self._STARTUP_GRACE_SECONDS
                and not self._tray_ref.has_open_dialog()):
            QTimer.singleShot(0, self._tray_ref._open_settings)
        return super().event(event)


# ──────────────────────────────────────────────────────────────────────
# Packaged-build self test
# ──────────────────────────────────────────────────────────────────────

def selftest() -> int:
    """Exercise everything a broken bundle usually loses. Returns the exit code."""
    problems: list = []
    report = [f"{APP_NAME} {__version__} selftest on {sys.platform}"]

    def check(name, fn):
        try:
            detail = fn()
            report.append(f"ok    {name}" + (f" — {detail}" if detail else ""))
        except Exception as exc:                        # noqa: BLE001 — report everything
            problems.append(name)
            report.append(f"FAIL  {name}: {exc!r}")

    def imports():
        import importlib
        for mod in ("sync.paths", "sync.lark_auth", "sync.lark_client", "sync.google_client",
                    "sync.sync_engine", "sync.lark_notifier", "app.autostart", "app.scheduler",
                    "app.oauth_worker", "app.about_dialog", "app.log_viewer",
                    "app.settings_dialog", "app.sync_thread"):
            importlib.import_module(mod)

    def tls_bundle():
        import certifi
        assert os.path.exists(certifi.where()), "CA bundle missing"
        return certifi.where()

    def icon():
        p = resource_path("assets/icon.png")
        assert p.exists(), f"missing {p}"
        assert not QIcon(str(p)).isNull(), "icon.png unreadable"
        return str(p)

    def drive_discovery():
        # Needs googleapiclient/discovery_cache/documents/drive.v3.json inside the bundle.
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        svc = build("drive", "v3", credentials=Credentials(token="x"), cache_discovery=False)
        assert hasattr(svc.files(), "create")

    def widgets():
        from app.settings_dialog import SettingsDialog
        from app.log_viewer import LogViewer
        cfg = ConfigManager()
        SettingsDialog(cfg).close()
        LogViewer(str(APP_DIR / "none.log")).close()
        SetupWizard(cfg).close()
        tray = TrayApp(cfg, QApplication.instance())
        tray._tray.hide()

    for name, fn in (("imports", imports), ("tls bundle", tls_bundle), ("icon asset", icon),
                     ("drive discovery doc", drive_discovery), ("widgets", widgets)):
        check(name, fn)

    report.append("RESULT " + ("FAILED: " + ", ".join(problems) if problems else "PASSED"))
    text = "\n".join(report)
    out = os.environ.get("LARKSYNC_SELFTEST_OUT") or str(APP_DIR / "selftest.txt")
    try:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    except OSError:
        pass
    if sys.stdout is not None:
        print(text)
    return 1 if problems else 0


def main():
    set_windows_app_id()
    app = LarkSyncApp(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)

    icon_path = resource_path("assets/icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    if "--selftest" in sys.argv:
        sys.exit(selftest())

    # ── Single instance ────────────────────────────────────────────
    # (v1.0.x only checked the sync lock, so a second copy happily started — and on
    # Windows its `os.kill(pid, 0)` check actually terminated the other process.)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    instance_lock = QLockFile(str(INSTANCE_LOCK_FILE))
    instance_lock.setStaleLockTime(0)     # stale only when the owning process is gone
    if not instance_lock.tryLock(300):
        QMessageBox.information(
            None, APP_NAME,
            f"LarkSync is already running.\nLook for the ⟳ icon in your {tray_location_hint()}."
        )
        return 0

    config = ConfigManager()

    # ── First run → show Setup Wizard ─────────────────────────────
    just_completed_setup = config.is_first_run() or not config.is_fully_configured()
    if just_completed_setup:
        wizard = SetupWizard(config)
        result = wizard.exec()
        if result != SetupWizard.DialogCode.Accepted:
            instance_lock.unlock()
            sys.exit(0)

    # NOTE: the per-sync lock (LOCK_FILE) is owned by SyncThread. Do NOT touch it here.

    # ── Start Tray App ────────────────────────────────────────────
    tray = TrayApp(config, app)
    app._tray_ref = tray                    # expose for dock-reopen handler

    # ── macOS native menu bar ─────────────────────────────────────
    if IS_MAC:
        app._menu_bar = build_menu_bar(config, tray)   # keep a reference alive

    tray.show_ready(first_time=just_completed_setup)

    code = app.exec()
    instance_lock.unlock()
    sys.exit(code)


if __name__ == "__main__":
    main()
