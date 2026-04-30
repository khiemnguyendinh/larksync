"""
Sync Thread
Runs the sync engine in a background QThread.
Emits signals for: progress updates, completion, errors.
Prevents concurrent runs via lock file.
"""

import logging
import os
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.config_manager import (
    ConfigManager, APP_DIR, STATE_FILE,
    LARK_TOKEN, GOOGLE_TOKEN, GOOGLE_CREDS, LOCK_FILE
)

logger = logging.getLogger(__name__)


class SyncThread(QThread):
    # Signals
    progress   = pyqtSignal(str)          # log line
    file_done  = pyqtSignal(int, int)     # (completed, total)
    finished   = pyqtSignal(dict)         # stats dict
    error      = pyqtSignal(str)          # fatal error message

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config   = config
        self._cancel  = False
        self._total   = 0
        self._done    = 0

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def cancel(self):
        self._cancel = True

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self):
        # ── Lock: prevent concurrent syncs ──────────────────────────
        if not self._acquire_lock():
            self.error.emit("Another sync is already running.")
            return

        stats = {"folders": 0, "files_synced": 0, "files_skipped": 0, "errors": 0}
        start = time.time()

        try:
            self._setup_logging()
            self.progress.emit("Starting sync…")

            # ── Lazy import (keeps startup fast) ────────────────────
            from sync.lark_auth   import get_valid_access_token
            from sync.lark_client import LarkClient
            from sync.google_client import GoogleDriveClient
            from sync.sync_engine import SyncEngine

            lark = LarkClient(
                app_id     = self.config.get("lark_app_id"),
                app_secret = self.config.get("lark_app_secret"),
            )
            gdrive = GoogleDriveClient(
                credentials_path = str(GOOGLE_CREDS),
                token_path       = str(GOOGLE_TOKEN),
            )

            # Compute last sync timestamp for incremental mode
            last_sync_ts = None
            last_sync_str = self.config.get("last_sync")
            if last_sync_str:
                try:
                    from datetime import datetime
                    last_sync_ts = datetime.fromisoformat(last_sync_str).timestamp()
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
            )

            stats = engine.run()

        except Exception as exc:
            msg = str(exc)
            logger.exception("Sync crashed")
            stats["errors"] += 1
            self.error.emit(msg)
        finally:
            self._release_lock()
            duration = time.time() - start
            stats["duration_seconds"] = duration

            # Save last sync info
            from datetime import datetime
            self.config.update({
                "last_sync":       datetime.now().isoformat(),
                "last_sync_stats": stats,
            })

            self.finished.emit(stats)

            # ── Lark notification ────────────────────────────────────
            self._send_lark_notification(stats, duration)

    # ------------------------------------------------------------------
    # Callbacks for engine
    # ------------------------------------------------------------------

    def _on_progress(self, message: str, completed: int = 0, total: int = 0):
        self.progress.emit(message)
        if total > 0:
            self.file_done.emit(completed, total)

    # ------------------------------------------------------------------
    # Lock file
    # ------------------------------------------------------------------

    def _acquire_lock(self) -> bool:
        if LOCK_FILE.exists():
            try:
                pid = int(LOCK_FILE.read_text().strip())
                # Check if that PID is still running
                os.kill(pid, 0)
                return False   # Process alive → another sync running
            except (ValueError, ProcessLookupError, PermissionError):
                pass           # Stale lock → remove and proceed
        LOCK_FILE.write_text(str(os.getpid()))
        return True

    def _release_lock(self):
        LOCK_FILE.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Logging setup
    # ------------------------------------------------------------------

    def _setup_logging(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        fmt = "%(asctime)s [%(levelname)s] %(message)s"
        logging.basicConfig(
            level    = logging.INFO,
            format   = fmt,
            handlers = [
                logging.FileHandler(str(APP_DIR / "sync.log"), encoding="utf-8"),
                logging.StreamHandler(),
            ],
            force = True,
        )

    # ------------------------------------------------------------------
    # Lark notification
    # ------------------------------------------------------------------

    def _send_lark_notification(self, stats: dict, duration: float):
        chat_id = self.config.get("lark_notify_chat_id", "")
        if not chat_id:
            return
        try:
            from sync.lark_auth    import get_valid_access_token
            from sync.lark_notifier import LarkNotifier
            notifier = LarkNotifier(
                access_token_fn = get_valid_access_token,
                chat_id         = chat_id,
            )
            if stats.get("errors", 0) > 0:
                notifier.notify_error(stats, duration)
            else:
                notifier.notify_success(stats, duration)
        except Exception as exc:
            logger.warning(f"Lark notification failed: {exc}")
