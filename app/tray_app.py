"""
Tray App
QSystemTrayIcon app — lives in the macOS menu bar / Windows system tray.
Handles: manual sync, scheduler (with catch-up after sleep / shutdown),
status display, settings access.
"""

import logging
import math
import time
from datetime import datetime

from PyQt6.QtCore    import QTimer, Qt, QObject, QPointF, QRectF, pyqtSlot
from PyQt6.QtGui     import (QIcon, QPixmap, QPainter, QColor, QFont, QAction,
                             QPen, QPolygonF)
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from app.config_manager  import ConfigManager, LOG_FILE
from app.platform_utils  import IS_MAC, tray_location_hint
from app.scheduler       import should_run, next_due, parse_iso
from app.sync_thread     import SyncThread
from app.settings_dialog import SettingsDialog
from app.log_viewer      import LogViewer
from app.version         import __version__

logger = logging.getLogger(__name__)

FOOTER_TEXT = "Sponsored by Kstudy Academy · www.kstudy.edu.vn"


class TrayApp(QObject):
    def __init__(self, config: ConfigManager, app: QApplication):
        super().__init__()
        self.config  = config
        self.app     = app
        self._thread: SyncThread | None = None
        self._syncing = False
        self._cancelling = False
        self._settings_dlg = None  # singleton guard
        self._menu_hidden_at: float = 0.0  # monotonic timestamp of last menu hide

        # ── Tray icon ─────────────────────────────────────────────────
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._make_icon(idle=True))
        self._tray.setToolTip("LarkSync")
        self._tray.activated.connect(self._on_tray_clicked)

        # ── Menu ──────────────────────────────────────────────────────
        self._menu = QMenu()
        # Record whenever the menu hides so we can suppress re-open on the
        # same click that dismissed it (macOS hides before `activated` fires).
        self._menu.aboutToHide.connect(self._on_menu_hidden)
        self._build_menu()
        if IS_MAC:
            # Do NOT call setContextMenu on macOS: Qt shows the context menu on
            # every left-click independently of the `activated` signal, which
            # prevents toggle-close behaviour.  We manage show/hide exclusively
            # through _on_tray_clicked → popup() / hide().
            pass
        else:
            # Windows (and Linux): the native context menu is what makes
            # right-click work and what closes the menu when you click away.
            self._tray.setContextMenu(self._menu)
        self._tray.show()

        # ── Scheduler ─────────────────────────────────────────────────
        # Polled every minute, so a missed slot is caught up within a minute of
        # the computer waking from sleep / being switched back on.
        self._scheduler_timer = QTimer()
        self._scheduler_timer.timeout.connect(self._check_schedule)
        self._scheduler_timer.start(60_000)
        self._check_schedule()               # also check immediately on launch

    # ── Menu construction ─────────────────────────────────────────────

    def _build_menu(self):
        self._menu.clear()
        self._menu.setStyleSheet("font-size: 13px;")

        # Title (non-interactive)
        title = QAction(f"LarkSync {__version__}", self._menu)
        title.setEnabled(False)
        title.setFont(self._bold_font())
        self._menu.addAction(title)
        self._menu.addSeparator()

        # Sync Now / Cancel
        if self._syncing:
            self._sync_action = QAction(
                "⟳  Cancelling…" if self._cancelling else "⟳  Syncing…", self._menu)
            self._sync_action.setEnabled(False)
            self._menu.addAction(self._sync_action)
            if not self._cancelling:
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

        if not IS_MAC:
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
        self._tray.setIcon(self._make_icon(idle=not self._syncing))

    # ── Sync control ──────────────────────────────────────────────────

    def _start_sync(self):
        if self._syncing:
            return
        # A previous run is still winding down (e.g. cancelled): never replace a live QThread.
        if self._thread is not None and self._thread.isRunning():
            return
        self._syncing = True
        self._cancelling = False
        self._refresh_menu()

        self._thread = SyncThread(self.config)
        self._thread.progress.connect(self._on_progress)
        self._thread.completed.connect(self._on_completed)
        self._thread.start()

        self._tray.showMessage(
            "LarkSync", "Sync started…",
            QSystemTrayIcon.MessageIcon.Information, 2000
        )

    def _cancel_sync(self):
        """Ask the worker to stop. The UI stays in 'busy' until the worker really ends,
        otherwise a second sync could be started on top of the first."""
        if self._thread and self._syncing and not self._cancelling:
            self._cancelling = True
            self._thread.cancel()
            self._refresh_menu()

    @pyqtSlot(str)
    def _on_progress(self, msg: str):
        self._tray.setToolTip(f"LarkSync — {msg}")

    @pyqtSlot(dict)
    def _on_completed(self, stats: dict):
        self._syncing = False
        self._cancelling = False
        self._refresh_menu()
        self._tray.setToolTip("LarkSync")

        errors = stats.get("errors", 0)
        synced = stats.get("files_synced", 0)
        dur    = self._fmt_duration(stats.get("duration_seconds", 0))
        fatal  = stats.get("fatal_error")

        if fatal:
            self._tray.showMessage(
                "LarkSync — Error", str(fatal)[:200],
                QSystemTrayIcon.MessageIcon.Critical, 6000
            )
        elif stats.get("cancelled"):
            self._tray.showMessage(
                "LarkSync — Cancelled",
                f"Stopped after {synced} files. Nothing is lost — the next sync continues.",
                QSystemTrayIcon.MessageIcon.Information, 4000
            )
        elif errors == 0:
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

    # ── Scheduler ─────────────────────────────────────────────────────

    def _schedule_args(self):
        return (
            self.config.get("schedule", "weekly"),
            self.config.get("schedule_day", "Monday"),
            self.config.get("schedule_hour", 8),
            self.config.get("schedule_minute", 0),
        )

    def _check_schedule(self):
        sched = self.config.get("schedule", "weekly")
        if sched == "manual" or self._syncing:
            return

        now  = datetime.now()
        last = parse_iso(self.config.get("last_sync"))

        # A brand-new install must not start a surprise full sync. Arm the schedule
        # from "now" instead: the first run happens at the next scheduled slot.
        # (v1.0.x never scheduled anything until the user had synced manually once.)
        anchor = parse_iso(self.config.get("schedule_anchor"))
        if last is None and anchor is None:
            self.config.set("schedule_anchor", now.isoformat())
            return

        if should_run(
            now, *self._schedule_args(),
            last_sync    = last,
            anchor       = anchor,
            last_attempt = parse_iso(self.config.get("last_attempt")),
            fail_streak  = int(self.config.get("fail_streak", 0) or 0),
        ):
            logger.info("Scheduled sync starting")
            self._start_sync()

    def _next_sync_str(self) -> str:
        nxt = next_due(datetime.now(), *self._schedule_args())
        if nxt is None:
            return "Manual only"
        return nxt.strftime("%a %b %d, %H:%M")

    def _last_sync_str(self) -> str:
        last = parse_iso(self.config.get("last_sync"))
        if not self.config.get("last_sync"):
            return "Never"
        return last.strftime("%b %d, %H:%M") if last else "Unknown"

    # ── UI actions ────────────────────────────────────────────────────

    def _on_menu_hidden(self):
        """Called by QMenu.aboutToHide — record when the menu was last dismissed."""
        self._menu_hidden_at = time.monotonic()

    def _on_tray_clicked(self, reason):
        if IS_MAC:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                # On macOS, the system dismisses the menu *before* `activated` fires,
                # so isVisible() is already False by the time we get here on a
                # second click.  Guard: if the menu was hidden within the last 350 ms
                # the click that closed it is the same physical click → don't reopen.
                if time.monotonic() - self._menu_hidden_at < 0.35:
                    return
                if self._menu.isVisible():
                    self._menu.hide()
                else:
                    self._menu.popup(self._tray.geometry().topLeft())
            return

        # Windows / Linux: right-click shows the native context menu (set above);
        # a left-click or double-click opens Settings.
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._open_settings()

    def show_ready(self, first_time: bool = False):
        """Show an orientation notification so users can find the tray icon."""
        where = tray_location_hint()
        if first_time:
            title = "LarkSync is ready"
            body  = f"Setup complete! LarkSync is now running in your {where}."
        else:
            title = "LarkSync is running"
            body  = (f"Find the ⟳ icon in your {where} "
                     "to sync, view logs, or open settings.")
        self._tray.showMessage(
            title, body,
            QSystemTrayIcon.MessageIcon.Information,
            8000,
        )

    def _open_settings(self):
        # If dialog is already open, bring it to front instead of opening a duplicate
        if self._settings_dlg is not None and self._settings_dlg.isVisible():
            self._settings_dlg.raise_()
            self._settings_dlg.activateWindow()
            return
        self._settings_dlg = SettingsDialog(self.config, tray_app=self)
        self._settings_dlg.exec()
        self._settings_dlg = None
        self._refresh_menu()  # schedule may have changed

    def _open_log(self):
        viewer = LogViewer(str(LOG_FILE))
        viewer.exec()

    def _open_about(self):
        from app.about_dialog import show_about
        show_about()

    def _quit(self):
        t = self._thread
        if t is not None and t.isRunning():
            t.cancel()
            if not t.wait(8000):          # stuck in a long export: don't hang the quit
                t.terminate()
                t.wait(1000)
        self.app.quit()

    def has_open_dialog(self) -> bool:
        return self._settings_dlg is not None or self.app.activeModalWidget() is not None

    # ── Icon generation ───────────────────────────────────────────────

    def _make_icon(self, idle: bool = True) -> QIcon:
        """
        Draw the tray icon.
        macOS  : black strokes on transparent, flagged as a template image, so
                 the system recolors it for light / dark menu bars.
        Windows: a template does not exist there and black-on-dark-taskbar is
                 invisible, so draw in brand blue (readable on light and dark).
        """
        logical = 18                       # drawing coordinate space
        if IS_MAC:
            px_size, dpr = logical * 2, 2  # Retina
            pen_color = QColor(0, 0, 0, 220) if idle else QColor(0, 0, 0, 140)
            width = 1.6
        else:
            px_size, dpr = 64, 1           # Windows scales 16–32 px from this
            pen_color = QColor(0, 122, 255) if idle else QColor(255, 149, 0)
            width = 2.0

        px = QPixmap(px_size, px_size)
        px.setDevicePixelRatio(dpr)
        px.fill(Qt.GlobalColor.transparent)

        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not IS_MAC:
            p.scale(px_size / logical, px_size / logical)

        pen = QPen(pen_color)
        pen.setWidthF(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Draw circular arrows (sync icon)
        cx, cy, r = logical / 2, logical / 2, 5.5

        # Arc — 300° sweep leaving a gap for arrowhead
        p.drawArc(
            QRectF(cx - r, cy - r, r * 2, r * 2),
            30 * 16,    # start angle (Qt uses 1/16 degree)
            300 * 16    # span angle
        )

        # Arrowhead at end of arc
        end_angle = math.radians(30)
        ax = cx + r * math.cos(end_angle)
        ay = cy - r * math.sin(end_angle)
        head_size = 2.8
        tip   = QPointF(ax, ay)
        left  = QPointF(ax - head_size * math.cos(end_angle + math.radians(150)),
                        ay + head_size * math.sin(end_angle + math.radians(150)))
        right = QPointF(ax - head_size * math.cos(end_angle - math.radians(150)),
                        ay + head_size * math.sin(end_angle - math.radians(150)))
        p.setBrush(pen_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([tip, left, right]))

        p.end()

        icon = QIcon(px)
        if IS_MAC:
            try:
                icon.setIsMask(True)       # template image → auto-inverts in dark mode
            except AttributeError:
                pass
        return icon

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
