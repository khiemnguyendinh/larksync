"""
Per-user data locations (no UI dependencies).

v1.1 stores user data in the OS-standard application-data folder instead of
~/Documents, because Documents can be synced to iCloud / OneDrive (which would
upload API secrets and OAuth tokens) and triggers a macOS privacy prompt:

    macOS    ~/Library/Application Support/LarkSync
    Windows  %APPDATA%\\LarkSync
    Linux    ~/.local/share/LarkSync            (development only)

Set LARKSYNC_HOME to override the location (used by the test-suite).
Data written by v1.0.x (~/Documents/lark_gdrive_sync) is copied over once by
`migrate_legacy_data()`; the old folder is left untouched.
"""

import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def _resolve_app_dir() -> Path:
    override = os.environ.get("LARKSYNC_HOME")
    if override:
        return Path(override).expanduser()
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "LarkSync"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or (home / "AppData" / "Roaming")) / "LarkSync"
    return Path(os.environ.get("XDG_DATA_HOME") or (home / ".local" / "share")) / "LarkSync"


APP_DIR        = _resolve_app_dir()
LEGACY_APP_DIR = Path.home() / "Documents" / "lark_gdrive_sync"

CONFIG_FILE         = APP_DIR / "app_config.json"
LOG_FILE            = APP_DIR / "sync.log"
STATE_FILE          = APP_DIR / "sync_state.json"
LARK_TOKEN          = APP_DIR / "lark_token.json"
GOOGLE_TOKEN        = APP_DIR / "google_token.json"
LEGACY_GOOGLE_TOKEN = APP_DIR / "google_token.pkl"      # v1.0.x pickle, migrated on first use
GOOGLE_CREDS        = APP_DIR / "credentials.json"
LOCK_FILE           = APP_DIR / "sync.lock"             # held while a sync is running
INSTANCE_LOCK_FILE  = APP_DIR / "instance.lock"         # held while the app is running

# Files copied from the legacy folder (everything LarkSync v1.0.x wrote).
_LEGACY_FILES = (
    "app_config.json", "lark_token.json", "google_token.pkl",
    "credentials.json", "sync_state.json", "sync.log",
)


def ensure_app_dir() -> Path:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        try:
            os.chmod(APP_DIR, 0o700)
        except OSError:
            pass
    return APP_DIR


def write_private(path: Union[str, Path], data: Union[str, bytes]) -> None:
    """
    Atomically write `data` to `path` (temp file + rename) with owner-only
    permissions where the OS supports them. Used for config and tokens, which
    contain secrets.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    binary = isinstance(data, bytes)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
            f.write(data)
        if sys.platform != "win32":
            os.chmod(tmp, 0o600)
        # Windows can briefly refuse the rename while an AV scanner holds the target.
        for attempt in range(5):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.1 * (attempt + 1))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def migrate_legacy_data(src: Path = None, dst: Path = None) -> list:
    """
    One-time copy of v1.0.x data into the new location.
    Runs only when the new folder has no config yet. Never overwrites, never
    deletes the source. Returns the list of file names copied.
    """
    src = Path(src) if src is not None else LEGACY_APP_DIR
    dst = Path(dst) if dst is not None else APP_DIR
    if (dst / "app_config.json").exists() or not (src / "app_config.json").exists():
        return []

    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in _LEGACY_FILES:
        s, d = src / name, dst / name
        if s.is_file() and not d.exists():
            try:
                shutil.copy2(s, d)
                if sys.platform != "win32":
                    os.chmod(d, 0o600)
                copied.append(name)
            except OSError as exc:
                logger.warning("Could not migrate %s: %s", name, exc)
    if copied:
        logger.info("Migrated %d file(s) from %s to %s", len(copied), src, dst)
    return copied
