"""
Sync Thread
Runs the sync engine in a background QThread.
Emits signals for: progress updates and a single completion event.
Prevents concurrent runs via a lock file.
"""

import logging
import sys
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QThread, QLockFile, pyqtSignal

from app.config_manager import (
    ConfigManager, APP_DIR, STATE_FILE, LOG_FILE,
    GOOGLE_TOKEN, GOOGLE_CREDS, LOCK_FILE,
)

logger = logging.getLogger(__name__)


class SyncThread(QThread):
    # Signals
    progress   = pyqtSignal(str)          # log line
    file_done  = pyqtSignal(int, int)     # (completed, total)
    # Exactly one of these ends every run. (v1.0.x redefined QThread's own
    # `finished` signal and emitted both `error` and `finished` after a crash,
    # so the error notification was immediately overwritten.)
    completed  = pyqtSignal(dict)         # stats dict (always has "cancelled" and "fatal_error")

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config   = config
        self._cancel  = False
        self._lock    = QLockFile(str(LOCK_FILE))
        self._lock.setStaleLockTime(0)    # a lock is stale as soon as its owner process is gone

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def cancel(self):
        self._cancel = True

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self):
        stats = {"folders": 0, "files_synced": 0, "files_skipped": 0, "errors": 0,
                 "cancelled": False, "fatal_error": None, "last_error": None}
        started_dt = datetime.now()
        start = time.time()

        # ── Lock: prevent concurrent syncs ──────────────────────────
        if not self._lock.tryLock(0):
            stats["fatal_error"] = "Another sync is already running."
            stats["duration_seconds"] = 0
            self.completed.emit(stats)
            return

        try:
            self._setup_logging()
            self.progress.emit("Starting sync…")

            # ── Lazy import (keeps startup fast) ────────────────────
            from sync.lark_client   import LarkClient
            from sync.google_client import GoogleDriveClient
            from sync.sync_engine   import SyncEngine

            lark = LarkClient(
                app_id     = self.config.get("lark_app_id"),
                app_secret = self.config.get("lark_app_secret"),
            )
            # interactive=False: a background sync must never pop a browser window.
            gdrive = GoogleDriveClient(
                credentials_path = str(GOOGLE_CREDS),
                token_path       = str(GOOGLE_TOKEN),
                interactive      = False,
            )
            gdrive.get_service()          # fail fast (and clearly) if Google needs re-authorizing

            # Incremental watermark = start of the last sync that finished with 0 errors.
            # (v1.0.x advanced it after crashes / cancels, so files that never synced were
            # skipped forever.) Falls back to last_sync for configs written by v1.0.x.
            last_sync_ts = None
            marker = self.config.get("last_sync_clean") or self.config.get("last_sync")
            if marker:
                try:
                    last_sync_ts = datetime.fromisoformat(marker).timestamp()
                except (ValueError, TypeError):
                    pass

            engine = SyncEngine(
                lark                  = lark,
                gdrive                = gdrive,
                state_path            = str(STATE_FILE),
                gdrive_root_folder_id = self.config.get("gdrive_root_folder_id") or None,
                progress_cb           = self._on_progress,
                cancel_fn             = lambda: self._cancel,
                max_file_mb           = self.config.get("max_file_mb", 100),
                sync_mode             = self.config.get("sync_mode", "incremental"),
                last_sync_ts          = last_sync_ts,
                conflict              = self.config.get("conflict", "overwrite"),
            )

            stats.update(engine.run())

        except Exception as exc:
            logger.exception("Sync crashed")
            stats["errors"] += 1
            stats["fatal_error"] = str(exc) or exc.__class__.__name__
        finally:
            self._lock.unlock()

        duration = time.time() - start
        stats["duration_seconds"] = duration
        self._record_result(stats, started_dt)

        # Notify the UI first, then tell Lark from a plain thread so a slow
        # network call cannot keep this QThread (and the "Syncing…" state) alive.
        self.completed.emit(stats)
        threading.Thread(
            target=self._send_lark_notification, args=(dict(stats), duration), daemon=True
        ).start()

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------

    def _record_result(self, stats: dict, started: datetime):
        now = datetime.now().isoformat()
        fatal = bool(stats["fatal_error"])
        updates = {"last_attempt": now, "last_sync_stats": stats}

        if fatal:
            # Nothing was synced (offline, expired token, …): do not move any marker,
            # so the scheduler retries soon instead of waiting a whole week.
            updates["fail_streak"] = int(self.config.get("fail_streak", 0) or 0) + 1
        elif stats["cancelled"]:
            updates["fail_streak"] = 0
        else:
            updates["fail_streak"] = 0
            updates["last_sync"] = now
            if stats["errors"] == 0:
                updates["last_sync_clean"] = started.isoformat()
        self.config.update(updates)

    # ------------------------------------------------------------------
    # Callbacks for engine
    # ------------------------------------------------------------------

    def _on_progress(self, message: str, completed: int = 0, total: int = 0):
        self.progress.emit(message)
        if total > 0:
            self.file_done.emit(completed, total)

    # ------------------------------------------------------------------
    # Logging setup
    # ------------------------------------------------------------------

    def _setup_logging(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        handlers = [
            # Rotating so sync.log cannot grow without bound on a weekly/daily job.
            RotatingFileHandler(str(LOG_FILE), maxBytes=2_000_000, backupCount=2,
                                encoding="utf-8", delay=True),
        ]
        # A windowed Windows / py2app build has no stderr — logging to None would just fail.
        if sys.stderr is not None:
            handlers.append(logging.StreamHandler())
        logging.basicConfig(
            level    = logging.INFO,
            format   = "%(asctime)s [%(levelname)s] %(message)s",
            handlers = handlers,
            force    = True,
        )

    # ------------------------------------------------------------------
    # Lark notification
    # ------------------------------------------------------------------

    def _send_lark_notification(self, stats: dict, duration: float):
        chat_id = self.config.get("lark_notify_chat_id", "")
        if not chat_id or stats.get("cancelled"):
            return
        try:
            from sync.lark_auth     import get_app_access_token
            from sync.lark_notifier import LarkNotifier
            notifier = LarkNotifier(
                access_token_fn = get_app_access_token,
                chat_id         = chat_id,
            )
            error_text = stats.get("fatal_error") or stats.get("last_error")
            if stats.get("errors", 0) > 0 or stats.get("fatal_error"):
                notifier.notify_error(stats, duration, error_text)
            else:
                notifier.notify_success(stats, duration)
        except Exception as exc:
            logger.warning(f"Lark notification failed: {exc}")
