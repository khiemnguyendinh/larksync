"""
Config Manager
Reads/writes app_config.json in the per-user data folder (see sync/paths.py).
All user data stays in that folder — never inside the .app bundle.
"""

import json
import logging
import os
import threading
from typing import Any

from sync.paths import (
    APP_DIR, CONFIG_FILE, LOG_FILE, STATE_FILE, LARK_TOKEN, GOOGLE_TOKEN,
    GOOGLE_CREDS, LOCK_FILE, INSTANCE_LOCK_FILE,
    ensure_app_dir, migrate_legacy_data, write_private,
)

# The path constants are re-exported: the UI modules import them from here.
__all__ = [
    "ConfigManager", "DEFAULTS",
    "APP_DIR", "CONFIG_FILE", "LOG_FILE", "STATE_FILE", "LARK_TOKEN",
    "GOOGLE_TOKEN", "GOOGLE_CREDS", "LOCK_FILE", "INSTANCE_LOCK_FILE",
]

logger = logging.getLogger(__name__)

DEFAULTS: dict = {
    "lark_app_id":          "",
    "lark_app_secret":      "",
    "gdrive_root_folder_id": "",
    "lark_notify_chat_id":  "",
    "schedule":             "weekly",   # weekly | daily | manual
    "schedule_day":         "Monday",
    "schedule_hour":        8,
    "schedule_minute":      0,
    "sync_mode":            "incremental", # incremental | full
    "conflict":             "overwrite",   # overwrite | skip
    "max_file_mb":          100,
    "launch_at_login":      False,
    "show_progress":        True,
    "first_run":            True,
    # Sync bookkeeping (written by SyncThread)
    "last_sync":            None,   # ISO time of the last sync that actually ran to the end
    "last_sync_clean":      None,   # ISO start time of the last sync with 0 errors → incremental watermark
    "last_attempt":         None,   # ISO time of the last attempt, whatever its outcome
    "fail_streak":          0,      # consecutive attempts that failed before syncing anything
    "schedule_anchor":      None,   # ISO time the schedule was first armed (see scheduler.py)
    "last_sync_stats":      None,
}


class ConfigManager:
    def __init__(self):
        ensure_app_dir()
        # v1.0.x kept its data in ~/Documents/lark_gdrive_sync — copy it over once.
        if "LARKSYNC_HOME" not in os.environ:
            try:
                migrate_legacy_data()
            except Exception:                       # never block start-up on migration
                logger.exception("Legacy data migration failed")

        self._lock = threading.RLock()              # SyncThread writes from a worker thread
        self._data: dict = dict(DEFAULTS)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if not isinstance(saved, dict):
                    raise ValueError("config root is not an object")
                self._data.update(saved)
            except (ValueError, OSError):
                # Corrupted config → keep a copy for the user, start fresh
                try:
                    os.replace(CONFIG_FILE, CONFIG_FILE.with_suffix(".json.bak"))
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Read / Write
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._save()

    def update(self, updates: dict) -> None:
        with self._lock:
            self._data.update(updates)
            self._save()

    def _save(self) -> None:
        # Contains the Lark App Secret → atomic write, owner-only permissions.
        write_private(
            CONFIG_FILE,
            json.dumps(self._data, indent=2, default=str, ensure_ascii=False),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_first_run(self) -> bool:
        return bool(self.get("first_run", True))

    def mark_setup_complete(self) -> None:
        self.set("first_run", False)

    def is_lark_configured(self) -> bool:
        return bool(self.get("lark_app_id") and
                    self.get("lark_app_secret") and
                    LARK_TOKEN.exists())

    def is_google_configured(self) -> bool:
        from sync.paths import LEGACY_GOOGLE_TOKEN
        return GOOGLE_CREDS.exists() and (GOOGLE_TOKEN.exists() or LEGACY_GOOGLE_TOKEN.exists())

    def is_fully_configured(self) -> bool:
        return self.is_lark_configured() and self.is_google_configured()

    # ------------------------------------------------------------------
    # Launch at login (macOS LaunchAgent / Windows Run key)
    # ------------------------------------------------------------------

    def set_launch_at_login(self, enabled: bool) -> bool:
        """Persist the preference and apply it to the OS. Returns True if the OS accepted it."""
        from app import autostart
        ok = autostart.set_enabled(enabled)
        self.set("launch_at_login", bool(enabled) if ok else autostart.is_enabled())
        return ok
