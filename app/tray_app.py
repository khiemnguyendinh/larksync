"""
Tray App
QSystemTrayIcon menu bar app — lives in Mac menu bar.
Handles: manual sync, weekly scheduler, status display, settings access.
Listens for Mac sleep/wake to reschedule missed syncs.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore    import QTimer, Qt, QObject, pyqtSlot
from PyQt6.QtGui     import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox, QWidget
)

from app.config_manager import ConfigManager, APP_DIR
from app.sync_thread    import SyncThread
from app.settings_dialog import SettingsDialog
from app.log_viewer      import LogViewer

logger = logging.getLogger(__name__)

FOOTER_TEXT = "Sponsored by Kstudy Academy · www.kstudy.edu.vn"


class TrayApp(QObject):
    def __init__(self, config: ConfigManager, app: QApplication):
        super().__init__()
        self.config  = config
        self.app     = app
        self._thread: SyncThread | None = None
        self._syncing = False

        # ── Tray icon ─────────────────────────────────────────────────
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._make_icon(idle=True))
        self._tray.setToolTip("LarkSync")
        self._tray.activated.connect(self._on_tray_clicked)

        # ── Menu ──────────────────────────────────────────────────────
        self._menu = QMenu()
        self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.show()

        # ── Scheduler ─────────────────────────────────────────────────
        self._scheduler_timer = QTimer()
        self._scheduler_timer.timeout.connect(self._check_schedule)
        self._scheduler_timer.start(60_000)  # check every minute
        self._check_schedule()               # also check immediately on launch

    # ── Menu construction ─────────────────────────────────────────────

    def _build_menu(self):
        self._menu.clear()
        self._menu.setStyleSheet("font-size: 13px;")

        # Title (non-interactive)
        title = QAction("LarkSync", self._menu)
        title.setEnabled(False)
        title.setFont(self._bold_font())
        self._menu.addAction(title)
        self._menu.addSeparator()

        # Sync Now / Cancel
        if self._syncing:
            self._sync_action = QAction("⟳  Syncing…", self._menu)
            self._sync_action.setEnabled(False)
            self._menu.addAction(self._sync_action)
            cancel = QAction("Cancel Sync", self._menu)
            cancel.triggered.connect(self._cancel_sync)
            self._menu.addAction(cancel)
        else:
            self._sync_action = QAction("Sync Now", self._menu)
            self._sync_action.triggered.connect(self._start_sync)
            self._menu.addAction(self._sync_action)

        self._menu.addSeparator()

        # Status lines
        last = self._last_sync_str()
        nxt  = self._next_sync_str()
        for txt in [f"Last sync: {last}", f"Next sync: {nxt}"]:
            a = QAction(txt, self._menu)
            a.setEnabled(False)
            a.setFont(self._small_font())
            self._menu.addAction(a)

        self._menu.addSeparator()

        settings_action = QAction("Settings…", self._menu)
        settings_action.triggered.connect(self._open_settings)
        self._menu.addAction(settings_action)

        log_action = QAction("View Log…", self._menu)
        log_action.triggered.connect(self._open_log)
        self._menu.addAction(log_action)

        import sys
        if sys.platform != "darwin":
            self._menu.addSeparator()
            about_action = QAction("About LarkSync", self._menu)
            about_action.triggered.connect(self._open_about)
            self._menu.addAction(about_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit LarkSync", self._menu)
        quit_action.triggered.connect(self._quit)
        self._menu.addAction(quit_action)

    def _refresh_menu(self):
        self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.setIcon(self._make_icon(idle=not self._syncing))

    # ── Sync control ──────────────────────────────────────────────────

    def _start_sync(self):
        if self._syncing:
            return
        self._syncing = True
        self._refresh_menu()

        self._thread = SyncThread(self.config)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self._on_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

        self._tray.showMessage(
            "LarkSync", "Sync started…",
            QSystemTrayIcon.MessageIcon.Information, 2000
        )

    def _cancel_sync(self):
        if self._thread:
            self._thread.cancel()
        self._syncing = False
        self._refresh_menu()

    @pyqtSlot(str)
    def _on_progress(self, msg: str):
        self._tray.setToolTip(f"LarkSync — {msg}")

    @pyqtSlot(dict)
    def _on_finished(self, stats: dict):
        self._syncing = False
        self._refresh_menu()
        errors = stats.get("errors", 0)
        synced = stats.get("files_synced", 0)
        dur    = self._fmt_duration(stats.get("duration_seconds", 0))

        if errors == 0:
            self._tray.showMessage(
                "LarkSync — Done",
                f"{synced} files synced in {dur}.",
                QSystemTrayIcon.MessageIcon.Information, 4000
            )
        else:
            self._tray.showMessage(
                "LarkSync — Finished with errors",
                f"{synced} synced, {errors} errors. Check View Log for details.",
                QSystemTrayIcon.MessageIcon.Warning, 5000
            )
        self._tray.setToolTip("LarkSync")

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._syncing = False
        self._refresh_menu()
        self._tray.showMessage(
            "LarkSync — Error",
            msg[:120],
            QSystemTrayIcon.MessageIcon.Critical, 6000
        )
        self._tray.setToolTip("LarkSync")

    # ── Scheduler ─────────────────────────────────────────────────────

    def _check_schedule(self):
        sched = self.config.get("schedule", "weekly")
        if sched == "manual" or self._syncing:
            return

        now      = datetime.now()
        last_str = self.config.get("last_sync")
        last     = datetime.fromisoformat(last_str) if last_str else None

        # Never auto-sync on first launch (no prior sync recorded)
        if last is None:
            return

        if sched == "daily":
            hour   = self.config.get("schedule_hour", 8)
            target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if now >= target and last.date() < now.date():
                self._start_sync()

        elif sched == "weekly":
            day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            target_day  = self.config.get("schedule_day", "Monday")
            target_hour = self.config.get("schedule_hour", 8)
            target_dow  = day_names.index(target_day)

            if (now.weekday() == target_dow and
                    now.hour >= target_hour and
                    (now - last).days >= 6):
                self._start_sync()

    def _next_sync_str(self) -> str:
        sched = self.config.get("schedule", "weekly")
        if sched == "manual":
            return "Manual only"
        now  = datetime.now()
        hour = self.config.get("schedule_hour", 8)
        if sched == "daily":
            t = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if t <= now:
                t += timedelta(days=1)
            return t.strftime("%b %d, %H:%M")
        # weekly
        day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        target_day = self.config.get("schedule_day", "Monday")
        target_dow = day_names.index(target_day)
        days_ahead = (target_dow - now.weekday()) % 7 or 7
        t = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=0, second=0, microsecond=0)
        return t.strftime("%a %b %d, %H:%M")

    def _last_sync_str(self) -> str:
        last_str = self.config.get("last_sync")
        if not last_str:
            return "Never"
        try:
            dt = datetime.fromisoformat(last_str)
            return dt.strftime("%b %d, %H:%M")
        except Exception:
            return "Unknown"

    # ── UI actions ────────────────────────────────────────────────────

    def _on_tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._menu.popup(self._tray.geometry().topLeft())

    def show_ready(self, first_time: bool = False):
        """Show an orientation notification so users can find the menu bar icon."""
        if first_time:
            title = "LarkSync is ready"
            body  = ("Setup complete! LarkSync is now running in your menu bar — "
                     "look for the ⟳ icon at the top-right of your screen.")
        else:
            title = "LarkSync is running"
            body  = ("Click the ⟳ icon in the menu bar (top-right of screen) "
                     "to sync, view logs, or open settings.")
        self._tray.showMessage(
            title, body,
            QSystemTrayIcon.MessageIcon.Information,
            8000,
        )

    def _open_settings(self):
        dlg = SettingsDialog(self.config, tray_app=self)
        dlg.exec()
        self._refresh_menu()  # schedule may have changed

    def _open_log(self):
        viewer = LogViewer(str(APP_DIR / "sync.log"))
        viewer.exec()

    def _open_about(self):
        import sys
        if sys.platform != "darwin":
            from app.win_menu import _show_about
            _show_about()

    def _quit(self):
        if self._syncing and self._thread:
            self._thread.cancel()
            self._thread.wait(3000)
        self.app.quit()

    # ── Icon generation ───────────────────────────────────────────────

    def _make_icon(self, idle: bool = True) -> QIcon:
        size = 22
        px   = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#34C759") if idle else QColor("#FFD60A")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(3, 3, 16, 16)
        p.setPen(QColor("white"))
        f = QFont("-apple-system", 10, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "⟳")
        p.end()
        return QIcon(px)

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _bold_font() -> QFont:
        f = QFont()
        f.setBold(True)
        return f

    @staticmethod
    def _small_font() -> QFont:
        f = QFont()
        f.setPointSize(11)
        return f

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        s = int(seconds)
        if s < 60:   return f"{s}s"
        m, s = divmod(s, 60)
        if m < 60:   return f"{m}m {s}s"
        h, m = divmod(m, 60)
        return f"{h}h {m}m"
