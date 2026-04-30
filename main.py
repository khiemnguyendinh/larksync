"""
LarkSync — Entry Point
1. Show Setup Wizard on first run
2. Start menu bar Tray App + native macOS menu bar
"""

import sys
import os
from pathlib import Path

# ── Ensure sync/ modules are importable ───────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore    import Qt, QEvent

from app.config_manager import ConfigManager, LOCK_FILE
from app.setup_wizard   import SetupWizard
from app.tray_app       import TrayApp

if sys.platform == "darwin":
    from app.mac_menu_bar import build_menu_bar, _open_settings
else:
    # Fallbacks for Windows
    def build_menu_bar(config, tray_app):
        return None
        
    def _open_settings(config, tray_app):
        from app.settings_dialog import SettingsDialog
        dlg = SettingsDialog(config, tray_app=tray_app)
        dlg.exec()
        tray_app._refresh_menu()


class LarkSyncApp(QApplication):
    """QApplication subclass — intercepts macOS dock-icon click to open Settings."""

    def __init__(self, argv):
        super().__init__(argv)
        self._tray_ref = None   # set after TrayApp is created

    def event(self, event: QEvent) -> bool:
        # ApplicationActivate fires when the user clicks the Dock icon while
        # the app is already running and no window is in front.
        if event.type() == QEvent.Type.ApplicationActivate and self._tray_ref:
            _open_settings(self._tray_ref.config, self._tray_ref)
        return super().event(event)


def main():
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
    app = LarkSyncApp(sys.argv)
    app.setApplicationName("LarkSync")
    app.setApplicationDisplayName("LarkSync")
    app.setQuitOnLastWindowClosed(False)

    # ── Check for stale lock from previous crash ───────────────────
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)
            QMessageBox.information(
                None, "LarkSync",
                "LarkSync is already running.\n"
                "Check the ⟳ icon in the menu bar."
            )
            return
        except (ValueError, ProcessLookupError, PermissionError):
            LOCK_FILE.unlink(missing_ok=True)

    config = ConfigManager()

    # ── First run → show Setup Wizard ─────────────────────────────
    just_completed_setup = config.is_first_run() or not config.is_fully_configured()
    if just_completed_setup:
        wizard = SetupWizard(config)
        result = wizard.exec()
        if result != SetupWizard.DialogCode.Accepted:
            sys.exit(0)

    # NOTE: LOCK_FILE is owned by SyncThread for sync-concurrency only.
    # Do NOT write it from main.py.

    # ── Start Tray App ────────────────────────────────────────────
    tray = TrayApp(config, app)
    app._tray_ref = tray                    # expose for dock-reopen handler

    # ── macOS native menu bar (if on macOS) ───────────────────────
    if sys.platform == "darwin":
        _menu_bar = build_menu_bar(config, tray)  # noqa: F841 — keep reference alive

    tray.show_ready(first_time=just_completed_setup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
