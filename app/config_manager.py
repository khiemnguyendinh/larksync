"""
Config Manager
Reads/writes app_config.json in ~/Documents/lark_gdrive_sync/
All user data stays in that folder — never inside the .app bundle.
"""

import json
import os
from pathlib import Path
from typing import Any

APP_DIR        = Path.home() / "Documents" / "lark_gdrive_sync"
CONFIG_FILE    = APP_DIR / "app_config.json"
LOG_FILE       = APP_DIR / "sync.log"
STATE_FILE     = APP_DIR / "sync_state.json"
LARK_TOKEN     = APP_DIR / "lark_token.json"
GOOGLE_TOKEN   = APP_DIR / "google_token.pkl"
GOOGLE_CREDS   = APP_DIR / "credentials.json"
LOCK_FILE      = Path.home() / ".larksync.lock"

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
    "last_sync":            None,
    "last_sync_stats":      None,
}


class ConfigManager:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = dict(DEFAULTS)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                # Corrupted config → start fresh
                pass

    # ------------------------------------------------------------------
    # Read / Write
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def update(self, updates: dict) -> None:
        self._data.update(updates)
        self._save()

    def _save(self) -> None:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_first_run(self) -> bool:
        return bool(self._data.get("first_run", True))

    def mark_setup_complete(self) -> None:
        self.set("first_run", False)

    def is_lark_configured(self) -> bool:
        return bool(self._data.get("lark_app_id") and
                    self._data.get("lark_app_secret") and
                    LARK_TOKEN.exists())

    def is_google_configured(self) -> bool:
        return GOOGLE_CREDS.exists() and GOOGLE_TOKEN.exists()

    def is_fully_configured(self) -> bool:
        return self.is_lark_configured() and self.is_google_configured()

    # ------------------------------------------------------------------
    # Launch at login (macOS LaunchAgent)
    # ------------------------------------------------------------------

    def set_launch_at_login(self, enabled: bool) -> None:
        self.set("launch_at_login", enabled)
        plist_dir  = Path.home() / "Library" / "LaunchAgents"
        plist_path = plist_dir / "com.larksync.agent.plist"
        app_path   = _get_app_executable()

        if enabled and app_path:
            plist_dir.mkdir(parents=True, exist_ok=True)
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>         <string>com.larksync.agent</string>
    <key>ProgramArguments</key>
    <array><string>{app_path}</string></array>
    <key>RunAtLoad</key>     <true/>
    <key>KeepAlive</key>     <false/>
</dict>
</plist>"""
            plist_path.write_text(plist)
            os.system(f'launchctl load "{plist_path}"')
        else:
            if plist_path.exists():
                os.system(f'launchctl unload "{plist_path}"')
                plist_path.unlink(missing_ok=True)


def _get_app_executable() -> str | None:
    """Return path to the running executable (works inside .app bundle too)."""
    import sys
    exe = sys.executable
    # Inside py2app bundle: .../LarkSync.app/Contents/MacOS/LarkSync
    if "LarkSync.app" in exe:
        return exe
    return exe  # dev mode: just use python interpreter path
