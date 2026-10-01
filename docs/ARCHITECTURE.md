# LarkSync — Architecture Reference

> **Audience:** Developers working on LarkSync source code.  
> **Last updated:** 2026-10-01 (v1.1.0)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layer Diagram](#2-layer-diagram)
3. [Module Reference](#3-module-reference)
4. [Application Startup Sequence](#4-application-startup-sequence)
5. [Sync Job Lifecycle](#5-sync-job-lifecycle)
6. [Signal / Slot Communication](#6-signal--slot-communication)
7. [Data Storage Schema](#7-data-storage-schema)
8. [Authentication Flows](#8-authentication-flows)
9. [Platform-Specific Code](#9-platform-specific-code)
10. [Build Pipeline](#10-build-pipeline)

---

## 1. System Overview

LarkSync is a **desktop tray application** (macOS menu bar / Windows system tray) that mirrors a Lark (Feishu) Drive folder to a Google Drive folder on a user-defined schedule.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER'S MACHINE                             │
│                                                                     │
│  ┌──────────────────┐    HTTP/REST    ┌──────────────────────────┐  │
│  │   Lark Drive     │◄───────────────│   LarkSync Desktop App   │  │
│  │  (Lark Open API) │                │                          │  │
│  └──────────────────┘                │  • Menu bar / tray icon  │  │
│                                      │  • Scheduled sync        │  │
│  ┌──────────────────┐    HTTP/REST   │  • Settings window       │  │
│  │  Google Drive    │◄───────────────│  • Log viewer            │  │
│  │  (Google API v3) │                └──────────────────────────┘  │
│  └──────────────────┘                                               │
│                                                                     │
│  Data dir: macOS ~/Library/Application Support/LarkSync/            │
│            Windows %APPDATA%\LarkSync\                              │
│    app_config.json   lark_token.json   google_token.json            │
│    sync_state.json   sync.log          credentials.json             │
└─────────────────────────────────────────────────────────────────────┘
```

**Technology stack**

| Layer         | Technology                                     |
|---------------|------------------------------------------------|
| UI framework  | PyQt6 (cross-platform)                         |
| Lark API      | `requests` + Lark Open API v1                  |
| Google API    | `google-api-python-client` + OAuth 2.0         |
| macOS bundle  | `py2app` → `.app` + `dmgbuild` → `.dmg`        |
| Windows bundle| `PyInstaller` → `.exe`                         |
| Windows installer | Inno Setup (`installer/windows/LarkSync.iss`) |
| CI/CD         | GitHub Actions (`build.yml`: tests on 3 OSes, macOS + Windows builds, draft release on `v*` tags) |

---

## 2. Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                      │
│                                                             │
│  TrayApp          SettingsDialog       SetupWizard          │
│  (tray_app.py)    (settings_dialog.py) (setup_wizard.py)    │
│                                                             │
│  LogViewer        mac_menu_bar.py      win_menu.py          │
│  (log_viewer.py)  [macOS only]         [Windows only]       │
│  about_dialog.py  oauth_worker.py (non-blocking sign-in)    │
└─────────────────────────┬───────────────────────────────────┘
                          │ reads/writes
┌─────────────────────────▼───────────────────────────────────┐
│                    APPLICATION LAYER                        │
│                                                             │
│  ConfigManager            SyncThread                        │
│  (config_manager.py)      (sync_thread.py)                  │
│  - app_config.json        - QThread subclass                │
│  scheduler.py (pure)      - QLockFile (one sync at a time)  │
│  autostart.py             - emits progress / completed      │
│  platform_utils.py                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │ drives
┌─────────────────────────▼───────────────────────────────────┐
│                       SYNC LAYER                            │
│                                                             │
│  SyncEngine          LarkClient         GoogleDriveClient   │
│  (sync_engine.py)    (lark_client.py)   (google_client.py)  │
│                                                             │
│  LarkAuth            LarkNotifier        paths.py           │
│  (lark_auth.py)      (lark_notifier.py)  (data dir, secrets)│
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Module Reference

### `main.py` — Entry point

| Responsibility | Details |
|---|---|
| Single-instance guard | `QLockFile(instance.lock)` — held for the life of the app; a crashed copy's lock is detected as stale (owner process gone). v1.0.x only checked the *sync* lock and, on Windows, `os.kill(pid, 0)` actually **terminated** the other process |
| First-run detection | If `config.is_first_run()` or credentials missing → open `SetupWizard` |
| Application subclass | `LarkSyncApp(QApplication)` — macOS only: Dock-click / re-activation re-opens Settings through `TrayApp._open_settings()` (skips the launch activation, never opens over another dialog) |
| Startup | `set_windows_app_id()` → `ConfigManager` (migrates v1.0.x data) → `TrayApp` → `build_menu_bar()` (macOS only) |
| `--selftest` | Imports every module, checks the CA bundle, `assets/icon.png`, the bundled Drive discovery document, builds the dialogs and tray; exits 0/1. CI runs it on the packaged `.app` / `.exe` |

---

### `sync/paths.py` — Data locations and safe writes

No UI dependencies. Resolves `APP_DIR` once at import time:

| Platform | `APP_DIR` |
|---|---|
| macOS | `~/Library/Application Support/LarkSync` |
| Windows | `%APPDATA%\LarkSync` |
| Linux (dev) | `~/.local/share/LarkSync` |
| any | `$LARKSYNC_HOME` if set (used by the tests and `--selftest`) |

v1.0.x used `~/Documents/lark_gdrive_sync`, which iCloud Drive / OneDrive may upload (including the App Secret and tokens) and which triggers a macOS privacy prompt. `migrate_legacy_data()` copies the known files over once (only if the new folder has no config; never overwrites; never deletes the old folder).

`write_private(path, data)` writes atomically (temp file + `os.replace`, with retries for Windows antivirus locks) and sets `0600` on POSIX. Config, both tokens and the sync state use it.

---

### `app/config_manager.py` — Configuration persistence

| Symbol | Type | Purpose |
|---|---|---|
| `APP_DIR` | `Path` | Re-exported from `sync/paths.py` |
| `CONFIG_FILE` | `Path` | Main config JSON |
| `LOG_FILE` | `Path` | `sync.log` — rotating (2 MB × 3 files) |
| `STATE_FILE` | `Path` | `sync_state.json` — Lark token → GDrive ID mapping |
| `LARK_TOKEN` | `Path` | Lark user OAuth token (JSON) |
| `GOOGLE_TOKEN` | `Path` | Google OAuth token (JSON; a v1.0.x `google_token.pkl` is migrated automatically) |
| `GOOGLE_CREDS` | `Path` | Google OAuth client credentials JSON |
| `LOCK_FILE` | `Path` | `sync.lock` — `QLockFile` held only while a sync runs |
| `INSTANCE_LOCK_FILE` | `Path` | `instance.lock` — held while the app runs |

`ConfigManager` wraps a dict with `get()` / `set()` / `update()`, guarded by an `RLock` (the sync worker thread writes bookkeeping keys). Every write is atomic (`write_private`). A corrupt config is moved to `app_config.json.bak` instead of being lost.

Bookkeeping keys written by `SyncThread`: `last_sync` (last run that reached the end), `last_sync_clean` (start time of the last run with **0 errors** — the incremental watermark), `last_attempt`, `fail_streak`, `schedule_anchor`, `last_sync_stats`.

---

### `app/autostart.py` — Launch at login

| Platform | Mechanism |
|---|---|
| macOS | `~/Library/LaunchAgents/com.larksync.agent.plist` running `/usr/bin/open -a <LarkSync.app>`. Only the plist is written — launchd loads it at the next login (bootstrapping now would start a second copy). Disabling runs `launchctl bootout` and removes the plist |
| Windows | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\LarkSync` = the real `LarkSync.exe` (or `pythonw.exe main.py` from source) |

Paths are built with `plistlib` / `subprocess.list2cmdline`, never string-interpolated. `ConfigManager.set_launch_at_login()` stores the state that is *actually in effect* if the OS refuses.

---

### `app/scheduler.py` — Schedule maths (pure functions)

`last_due(now, …)` is the most recent scheduled moment ≤ now; `should_run()` is true when the later of `last_sync` and `schedule_anchor` is before it. That gives catch-up after sleep / shutdown for free, treats a manual sync after the slot as satisfying it, and re-arms the schedule when Settings changes it. Failed attempts (`fail_streak`) retry after 15 min, doubling up to 4 h; after 6 failed attempts in a row it waits for the next slot.

---

### `app/tray_app.py` — System tray / menu bar

`TrayApp(QObject)` is the central controller of the running application.

**Key responsibilities:**

| Method | Purpose |
|---|---|
| `_build_menu()` | Constructs the QMenu each time state changes |
| `_refresh_menu()` | Rebuilds menu + updates tray icon |
| `_start_sync()` | Refuses while a thread is still alive; creates `SyncThread`, connects `progress`/`completed`, starts it |
| `_cancel_sync()` | Calls `SyncThread.cancel()` and shows "Cancelling…"; the UI stays busy until `completed` arrives |
| `_check_schedule()` | Called by a 60-second `QTimer` (so a missed slot is caught up within a minute of waking); delegates to `scheduler.should_run()` |
| `_on_tray_clicked()` | **macOS:** toggle (show on first click, hide on second). **Windows/Linux:** the native context menu (right-click) is attached with `setContextMenu`; left-click / double-click open Settings |
| `_open_settings()` | **Singleton guard**: raises existing dialog if open, otherwise creates one |
| `_make_icon()` | macOS: black Retina-scaled *template* image (the OS recolors it). Windows: blue (idle) / orange (syncing) 64 px pixmap — a black icon is invisible on the default dark taskbar |
| `_quit()` | Cancels a running sync, waits 8 s, then terminates the thread so quitting never hangs or crashes |

**Singleton settings guard:**
```python
self._settings_dlg = None   # set in __init__

def _open_settings(self):
    if self._settings_dlg is not None and self._settings_dlg.isVisible():
        self._settings_dlg.raise_()
        self._settings_dlg.activateWindow()
        return
    self._settings_dlg = SettingsDialog(self.config, tray_app=self)
    self._settings_dlg.exec()   # blocks — but Qt event loop still runs
    self._settings_dlg = None
    self._refresh_menu()
```

**Scheduler logic** (`_check_schedule()` → `app/scheduler.py`):
- Reads `config.schedule` → `weekly` | `daily` | `manual`
- First launch with no `last_sync`: stores `schedule_anchor = now` and returns (no surprise full sync); the first run is the next slot
- Otherwise `should_run()` compares the most recent slot with `max(last_sync, schedule_anchor)` — missed slots are caught up
- Timer ticks every **60 seconds**

---

### `app/settings_dialog.py` — Settings window

Tabbed `QDialog` with four tabs: **General**, **Larksuite**, **Google Drive**, **Notifications**.

**Important classes/helpers:**

| Symbol | Purpose |
|---|---|
| `_SecretField(QWidget)` | Password-mode QLineEdit + 👁 eye toggle button. Exposes `.text()`, `.setText()`, `.textChanged` to match `QLineEdit` API |
| `_input()` | Factory for styled `QLineEdit` |
| `_combo()` | Factory for styled `QComboBox` |
| `_section_title()` | Uppercase section header label |
| `_dark()` | Returns `True` if system is in dark mode |

**Button state machine:**

```
[Initial state]
  Cancel: dimmed/disabled      Save: enabled      Sync Now: enabled (blue)

[User edits any field]
  Cancel: enabled (closes without saving)

[Save clicked]
  Settings persisted (login item applied if it changed), dialog closes, no sync

[Sync Now clicked]
  Settings persisted, Sync Now → "Cancel Sync" (red), status "⏳ Syncing…"
  _watch_sync_done() polls tray_app._syncing every 1 s

[Cancel Sync clicked]
  tray_app._cancel_sync(); button → "Cancelling…" (disabled) until the worker really ends

[Sync ends]
  Button restored; status shows the outcome read from config["last_sync_stats"]
  (complete / cancelled / N errors / fatal error text)
```

`_apply_updates()` compares the new "Launch at Login" value with the value **before** saving (v1.0.x compared afterwards, so the OS entry was never changed) and re-arms `schedule_anchor` when the schedule changed.

**Sign-in buttons** start `LarkAuthWorker` / `GoogleAuthWorker` (`app/oauth_worker.py`, QThreads reporting through `succeeded` / `failed`), so the window stays responsive while the browser flow runs; closing the dialog cancels a pending Lark sign-in and frees port 8080.

---

### `app/sync_thread.py` — Background sync worker

`SyncThread(QThread)` runs the entire sync job off the main thread.

**Signals:**

| Signal | Type | Emitted when |
|---|---|---|
| `progress` | `str` | Each file processed (log line) |
| `file_done` | `(int, int)` | `(completed, total)` |
| `completed` | `dict` | **Exactly once per run.** Stats plus `cancelled` (bool) and `fatal_error` (str or `None`) |

(v1.0.x redefined `QThread.finished` and emitted both `error` and `finished` after a crash, so the error balloon was immediately replaced by a "0 files synced" one.)

**Lock protocol:** `QLockFile(sync.lock)`, `setStaleLockTime(0)` (stale only when the owner process is gone). `tryLock(0)` fails → `completed` with `fatal_error="Another sync is already running."`.

**Bookkeeping (`_record_result`) — what moves which marker:**

| Outcome | `last_sync` | `last_sync_clean` (incremental watermark) | `fail_streak` |
|---|---|---|---|
| Clean run (0 errors) | now | run start time | reset to 0 |
| Run with per-file errors | now | unchanged — failed files are retried next time | reset to 0 |
| Cancelled | unchanged | unchanged | reset to 0 |
| Fatal (offline, token expired…) | unchanged | unchanged | +1 → scheduler retries with back-off |

v1.0.x advanced `last_sync` after every run, including crashes and cancels, so incremental mode then skipped files that had never been uploaded.

**Other behaviour:** the Google client is created with `interactive=False` and `get_service()` is called up front, so an expired authorization fails fast with a clear message instead of opening a browser in the background. Logging uses a `RotatingFileHandler` (2 MB × 3) and only adds a `StreamHandler` when `sys.stderr` exists (windowed builds have none). The Lark notification is sent from a plain daemon thread *after* `completed`, so a slow network call can't keep the "Syncing…" state alive.

---

### `sync/lark_auth.py` — Lark OAuth

Two distinct token types:

| Token | Function | Used by |
|---|---|---|
| `user_access_token` | Scoped `drive:drive:readonly` — user's personal Drive | `LarkClient` (Drive read) |
| `app_access_token` | App-level tenant token | `LarkNotifier` (send messages) |

**OAuth flow (`authorize(timeout=180, cancel_event=None)`)** — blocking, run it from a worker thread:
1. Binds `127.0.0.1:8080` (fails with a readable "port in use" error; on Windows `SO_REUSEADDR` is off so the conflict is really detected)
2. Opens the browser to the Lark authorization URL with a random `state`
3. Serves `/callback` until a code arrives, the timeout passes or `cancel_event` is set; a callback whose `state` doesn't match is rejected
4. **Always** closes the server (v1.0.x left port 8080 bound after a timeout, so every retry failed)
5. Exchanges the code via `/authen/v1/oidc/access_token`, saves `lark_token.json` (0600)

**Auto-refresh (`get_valid_access_token()`):**
- Checks `obtained_at + expire_in - 300` (5-min buffer)
- Calls `_refresh_token()` if within buffer
- Raises `LarkAuthRequired` (a `LarkAuthError`) when there is no token, no refresh token, or Lark rejects the refresh — the message tells the user to re-authorize in Settings. A Lark outage (5xx) is *not* reported as an expired authorization

---

### `sync/lark_client.py` — Lark Drive API

| Method | API endpoint | Notes |
|---|---|---|
| `list_folder(token)` | `GET /drive/v1/files` | Paginated (200/page) |
| `traverse(token, path)` | recursive DFS via `list_folder` | Returns flat list with `.path` and `.parent_token` |
| `export_native_file(token, type)` | `POST /drive/v1/export_tasks` then poll + download | 3-step async export |
| `download_file(token, max_bytes=0)` | `GET /drive/v1/files/{token}/download` | Regular files; the size limit is enforced from `Content-Length` (the file list has no size) and raises `FileTooLarge`, which the engine counts as *skipped*, not an error |

Every call goes through `_request()`: up to 3 retries with back-off on 429 / 500 / 502 / 503 / 504 and dropped connections (honours `Retry-After`). `traverse(..., cancel_fn)` stops early when the user cancels, so Cancel works during a long listing.

**File type mapping:**

```python
LARK_EXPORT_MAP = {
    "docx":     "docx",   # Lark Doc       → Word
    "doc":      "docx",   # Lark Doc (old) → Word
    "sheet":    "xlsx",   # Lark Sheet     → Excel
    "bitable":  "xlsx",   # Lark Base      → Excel
    "mindnote": "pdf",    # MindNote       → PDF
    "slides":   "pptx",   # Lark Slides    → PowerPoint
}
```

**Native file export sequence:**
```
POST /drive/v1/export_tasks   → ticket
GET  /drive/v1/export_tasks/{ticket}  (poll every 2s with backoff → 10s max)
  job_status: 0 = done, 1/2 = in-progress, other = error
GET  /drive/v1/export_tasks/file/{export_token}/download
```

---

### `sync/google_client.py` — Google Drive API

Uses Google OAuth 2.0 with `drive` scope (read + write). Token stored as JSON at `google_token.json` (0600). A v1.0.x `google_token.pkl` is read once, re-saved as JSON and deleted.

`GoogleDriveClient(credentials_path, token_path, interactive=True)`: with `interactive=False` (background syncs) an expired/revoked authorization raises `GoogleAuthRequired` instead of opening a browser. OAuth apps in *Testing* status lose refresh tokens after 7 days, so this is a routine case.

| Method | API call | Notes |
|---|---|---|
| `get_or_create_folder(name, parent)` | `files.list` → `files.create` | Idempotent — won't create duplicates |
| `find_item(name, parent, is_folder)` | `files.list` with `q=` filter | Escapes single-quotes in names. `parent=None` is anchored to `'root'` (v1.0.x matched a same-named folder *anywhere* in the Drive) |
| `upload_file(content, filename, ext, parent, existing_id)` | `files.create` or `files.update` | If `existing_id` → overwrite (falls back to create when that file was deleted/trashed in Drive); if ext is docx/xlsx/pptx → set `mimeType` to Google native format for in-Drive editing; uploads > 5 MB are resumable |

All calls pass `supportsAllDrives=True` (Shared Drives work) and `num_retries=3`.

**MIME type conversion for Google native formats:**

```python
GOOGLE_NATIVE_MIME = {
    "docx": "application/vnd.google-apps.document",
    "xlsx": "application/vnd.google-apps.spreadsheet",
    "pptx": "application/vnd.google-apps.presentation",
}
```

---

### `sync/sync_engine.py` — Core sync logic

`SyncEngine` orchestrates the full sync job.

**State file (`sync_state.json`) schema:**
```json
{
  "folders": {
    "<lark_folder_token>": "<gdrive_folder_id>",
    ...
  },
  "files": {
    "<lark_file_token>": "<gdrive_file_id>",
    ...
  }
}
```

**`run()` algorithm:**
1. Call `lark.traverse("")` → flat list of all items (cancellable)
2. For each item:
   - If `type == "folder"` → `_sync_folder()` (always, to preserve structure)
   - If `type == "shortcut"` → skipped (its target is synced from its own folder)
   - If file:
     - Incremental mode: skip if `modified_time` / `created_time` ≤ `last_sync_ts` (the last *clean* sync)
     - `conflict == "skip"` and the file is already mirrored → skipped before downloading (v1.0.x offered this option in the UI but ignored it)
     - Full mode: always sync
3. `_sync_file()`: download/export → `gdrive.upload_file()`
4. State is saved every 25 items and in a `finally` block, so a cancel or crash never loses the mapping (which would cause duplicate uploads next run)

Returns `folders`, `files_synced`, `files_skipped`, `errors`, `cancelled`, `last_error`. A corrupt `sync_state.json` is moved to `.bak` and the run starts fresh.

**Incremental filtering (`_is_modified_since_last_sync()`):**
- Lark timestamps are returned as strings or ints — normalized to `float` via `_ts()` helper
- Falls back to "sync it" if timestamp is missing or zero

**`.url` file resolution:**
- Some Lark shortcuts are Windows `.url` files pointing to Lark doc URLs
- `_resolve_url_file()` parses the URL, identifies the doc type from path segments, extracts the doc token, and exports it like a native file

---

### `sync/lark_notifier.py` — Lark group chat notifications

Sends a Lark **interactive card** message to a group chat after each sync.

- Uses **app access token** (not user token) via `get_app_access_token()`
- Sends to `POST /im/v1/messages?receive_id_type=chat_id`
- Notification failure never crashes the sync (wrapped in `try/except`)
- Two card templates: green (success) / red (error with details)

---

### `app/mac_menu_bar.py` — macOS native application menu

On macOS, creates a `QMenuBar(None)` which becomes the global app menu bar (top of screen).

- **File menu**: Sync Now (⌘R), View Log… (⌘L), Settings (⌘,), Quit LarkSync (⌘Q)
- **Help menu**: Links to Lark app creation, Google API credentials, finding Lark Chat ID + About dialog

`_open_settings()` delegates to `tray_app._open_settings()` to share the singleton guard.

---

### `app/setup_wizard.py` — First-run Setup Wizard

A multi-page `QDialog` shown only on first launch or when credentials are missing. Guides the user through:

1. Lark App ID + Secret input, then **Authorize Lark** (worker thread)
2. Google `credentials.json` upload, optional destination folder ID, then **Authorize Google** (worker thread)
3. Preferences: schedule, conflict handling, optional Lark chat ID
4. Summary → **Start LarkSync** (asks for confirmation if Lark or Google is not connected yet)

---

## 4. Application Startup Sequence

```
main.py::main()
    │
    ├─ 0. set_windows_app_id(), QApplication, window icon
    │       `--selftest` → run selftest(), exit
    │
    ├─ 1. QLockFile(instance.lock).tryLock()   (single-instance guard)
    │       Another copy running → message → exit
    │
    ├─ 2. ConfigManager() → migrate v1.0.x data (once), read app_config.json
    │
    ├─ 3. is_first_run() or not is_fully_configured()?
    │    ├─ YES → SetupWizard().exec()
    │    │         If rejected → sys.exit(0)
    │    └─ NO  → continue
    │
    ├─ 4. TrayApp(config, app)
    │       ├─ QSystemTrayIcon + QMenu (context menu attached on Windows/Linux)
    │       ├─ Starts scheduler QTimer (60s)
    │       └─ Calls _check_schedule() immediately
    │
    ├─ 5. [macOS only] build_menu_bar(config, tray)
    │       Creates native macOS menu bar
    │
    ├─ 6. tray.show_ready(first_time=...)
    │       Shows welcome notification
    │
    └─ 7. app.exec() — Qt main event loop
```

---

## 5. Sync Job Lifecycle

```
User/Scheduler triggers _start_sync()
    │
    ▼
SyncThread.start()         [new OS thread]
    │
    ├─ QLockFile(sync.lock).tryLock(0)
    │   Held by another process → completed(fatal_error), return
    │
    ├─ _setup_logging()   RotatingFileHandler → <APP_DIR>/sync.log
    │
    ├─ LarkClient(app_id, app_secret)
    ├─ GoogleDriveClient(creds_path, token_path, interactive=False)
    ├─ gdrive.get_service()   → GoogleAuthRequired fails fast with a clear message
    │
    ├─ SyncEngine.run()
    │   ├─ lark.traverse("") → flat list of all Lark items   (cancellable)
    │   │
    │   └─ for each item (cancel checked each iteration):
    │       ├─ is folder → _sync_folder()
    │       │   └─ gdrive.get_or_create_folder() → save to state
    │       │
    │       └─ is file:
    │           ├─ shortcut → skip
    │           ├─ [incremental] skip if not modified since last clean sync
    │           ├─ [conflict=skip] skip if already mirrored
    │           ├─ lark native? → export_native_file() [3-step async]
    │           ├─ regular?     → download_file(max_bytes)
    │           ├─ .url file?   → _resolve_url_file() → export
    │           └─ gdrive.upload_file() [create or overwrite]
    │               └─ save file token → GDrive ID to state
    │   (finally: save state)
    │
    ├─ [finally] unlock sync.lock
    ├─ _record_result(): last_attempt / last_sync / last_sync_clean / fail_streak
    ├─ emit completed(stats)
    │
    └─ daemon thread: _send_lark_notification(stats)
         LarkNotifier.notify_success() or notify_error()
         POST /im/v1/messages        (skipped when cancelled)
```

---

## 6. Signal / Slot Communication

```
SyncThread (background thread)         TrayApp / SettingsDialog (main thread)
─────────────────────────────          ─────────────────────────────────────
progress(str)          ──────────────► _on_progress(msg)
                                         tray.setToolTip(...)

file_done(int, int)    ──────────────► [not currently connected in TrayApp]
                                         available for progress bar use

completed(dict)        ──────────────► _on_completed(stats)
                                         _syncing = False, _refresh_menu()
                                         one balloon: Error / Cancelled / Done /
                                         Finished with errors
```

OAuth workers (`app/oauth_worker.py`):

```
LarkAuthWorker / GoogleAuthWorker (QThread) ──► succeeded() / failed(str)
                                                 → SettingsDialog / SetupWizard slots
```

PyQt6 signals are thread-safe for cross-thread connections — Qt queues them on the receiver's event loop automatically. (Do **not** use `QTimer.singleShot` from a plain Python thread to reach the UI: that thread has no event loop, so the callback never runs — which is how v1.0.x's wizard sign-in status never updated.) Workers keep themselves alive in a module-level set until they finish, because destroying a running `QThread` aborts the process.

`SettingsDialog._watch_sync_done()` polls `tray_app._syncing` every 1 second via a `QTimer.singleShot` chain (main thread) to restore the "Sync Now" button after the sync completes.

---

## 7. Data Storage Schema

All user data lives in **`APP_DIR`** (see [`sync/paths.py`](#syncpathspy--data-locations-and-safe-writes): `~/Library/Application Support/LarkSync` on macOS, `%APPDATA%\LarkSync` on Windows). Nothing is stored inside the app bundle. Files holding secrets are written atomically with owner-only permissions.

### `app_config.json`

```json
{
  "lark_app_id":           "cli_xxxxxxxxx",
  "lark_app_secret":       "xxxxxxxxxxxxxxxx",
  "gdrive_root_folder_id": "1aBcDeFgH...",
  "lark_notify_chat_id":   "oc_xxxxxxxxxxxxxxxx",
  "schedule":              "weekly",
  "schedule_day":          "Monday",
  "schedule_hour":         8,
  "schedule_minute":       0,
  "sync_mode":             "incremental",
  "conflict":              "overwrite",
  "max_file_mb":           100,
  "launch_at_login":       false,
  "show_progress":         true,
  "first_run":             false,
  "last_sync":             "2026-04-30T21:00:00.000000",
  "last_sync_clean":       "2026-04-30T20:58:12.000000",
  "last_attempt":          "2026-04-30T21:00:00.000000",
  "fail_streak":           0,
  "schedule_anchor":       "2026-04-24T09:30:00.000000",
  "last_sync_stats":       {"folders": 5, "files_synced": 42, "errors": 0, "cancelled": false, "fatal_error": null}
}
```

### `sync_state.json`

```json
{
  "folders": {
    "FolderToken123": "1AbCdEfGhIjK...",
    "FolderToken456": "1XyZaBcDeFgH..."
  },
  "files": {
    "FileToken789":   "1MnOpQrStUvW...",
    "FileTokenABC":   "1QrStUvWxYzA..."
  }
}
```

Used to detect existing GDrive files for overwrite vs create decisions.

### `lark_token.json`

Standard Lark OIDC token response plus `obtained_at`:
```json
{
  "access_token":  "u-xxx",
  "refresh_token": "r-xxx",
  "token_type":    "Bearer",
  "expire_in":     7200,
  "obtained_at":   1746000000.0
}
```

### `credentials.json`

Standard Google OAuth 2.0 client credentials (downloaded from Google Cloud Console):
```json
{
  "installed": {
    "client_id":     "123456789.apps.googleusercontent.com",
    "client_secret": "GOCSPX-xxx",
    "redirect_uris": ["http://localhost"],
    ...
  }
}
```

### `google_token.json`

`Credentials.to_json()` output (token, refresh token, client id/secret, scopes). Managed by `GoogleDriveClient`. Replaces the pickle used by v1.0.x (`google_token.pkl`), which is migrated and deleted on first use — unpickling a file is only as safe as the folder it sits in, and pickles break across Python upgrades.

---

## 8. Authentication Flows

### 8.1 Lark User OAuth (initial authorization)

```
Setup Wizard / "Re-authorize Lark" button
    │
    ▼
LarkAuthWorker (QThread) → lark_auth.authorize()
    │
    ├─ Bind HTTPServer on 127.0.0.1:8080 (closed in `finally`)
    │
    ├─ Open browser:
    │   https://open.larksuite.com/open-apis/authen/v1/authorize
    │     ?app_id=cli_xxx&redirect_uri=http://localhost:8080/callback
    │     &scope=drive:drive:readonly&state=<random>
    │
    ├─ User logs in → Lark redirects to localhost:8080/callback?code=xxx&state=<random>
    │   (state is verified; mismatches are rejected)
    │
    ├─ _exchange_code(code):
    │   POST /authen/v1/oidc/access_token
    │   {grant_type: authorization_code, code: xxx}
    │   Headers: Authorization: Bearer <app_access_token>
    │
    └─ save_token(token_data) → lark_token.json
```

### 8.2 Lark App Access Token (for notifications)

```
get_app_access_token()
    │
    └─ POST /auth/v3/app_access_token/internal
       {app_id: xxx, app_secret: xxx}
       Returns: {app_access_token: "t-xxx", expire: 7200}
```

This is a fresh call every time — no caching needed (tokens are valid 2h, notifications are rare).

### 8.3 Google OAuth (initial authorization)

```
"Authorize Google" / "Re-authorize Google" button
    │
    ▼
GoogleAuthWorker (QThread) → GoogleDriveClient(interactive=True).get_service()
    └─ _get_credentials()
        ├─ Load google_token.json (or migrate a legacy .pkl)
        ├─ If valid → use it
        ├─ If expired + has refresh_token → creds.refresh(Request())
        │     RefreshError → interactive? fall through : raise GoogleAuthRequired
        └─ Else: InstalledAppFlow.run_local_server(port=0, timeout_seconds=180)
                 Opens browser → user authorizes → code callback
                 Saves fresh token to google_token.json

Background syncs use interactive=False and never reach the last branch.
```

---

## 9. Platform-Specific Code

### macOS

| Module | Mac-specific behavior |
|---|---|
| `mac_menu_bar.py` | `QMenuBar(None)` → global app menu bar; `QKeySequence("Ctrl+,")` → ⌘, on macOS |
| `tray_app.py::_make_icon()` | 36×36 Retina pixmap (18pt @2x); `setIsMask(True)` marks as template image — macOS inverts automatically in dark menu bar |
| `tray_app.py::_on_tray_clicked()` | Handles `Trigger` activation reason for left-click; toggles menu (no `setContextMenu` on macOS) |
| `autostart.py` | LaunchAgent plist → `~/Library/LaunchAgents/com.larksync.agent.plist` running `open -a LarkSync.app` |
| `main.py::LarkSyncApp.event()` | Intercepts `ApplicationActivate` to re-open Settings on Dock click (2 s start-up grace, never over another dialog) |
| `sync/paths.py` | `~/Library/Application Support/LarkSync` |
| `setup.py` / `build.sh` | `py2app` configuration + trimming + self-test + signing + `.dmg` |

### Windows

| Module | Windows-specific behavior |
|---|---|
| `tray_app.py` | `setContextMenu()` for right-click; left-click opens Settings; coloured icon (a black template icon is invisible on a dark taskbar) |
| `win_menu.py` | Thin wrapper over the shared About dialog (macOS uses the native Help menu) |
| `autostart.py` | Writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`; from source it uses `pythonw.exe main.py` |
| `platform_utils.py::set_windows_app_id()` | `SetCurrentProcessExplicitAppUserModelID` so toasts/taskbar show "LarkSync" |
| `sync/lark_auth.py` | Loopback server without `SO_REUSEADDR` (so "port in use" is detected) |
| `sync/paths.py` | `%APPDATA%\LarkSync`; atomic replace retries for antivirus locks |
| `build_windows.py` | PyInstaller (`os.pathsep` for `--add-data`, version-info resource, only `drive.v3.json` bundled) |
| `installer/windows/LarkSync.iss` | Per-user Inno Setup installer |
| `requirements_windows.txt` | Runtime packages + `pyinstaller` |

### Conditional imports pattern

```python
import sys

from app.platform_utils import IS_MAC, IS_WIN      # sys.platform == "darwin" / "win32"

if IS_MAC:
    from app.mac_menu_bar import build_menu_bar
```

Platform detection uses `sys.platform` (`"darwin"` / `"win32"`), never host-name or environment variables. The platform flags are module-level so the tests can monkeypatch them and exercise both code paths on one OS.

---

## 10. Build Pipeline

### macOS build (`bash build.sh`)

```
build.sh
    │
    ├─ 1. venv + pip install -r requirements_macos.txt   (SKIP_VENV=1 in CI)
    ├─ 2. [ICON_SRC=… only] sips/iconutil → assets/icon.icns
    ├─ 3. python setup.py py2app → dist/LarkSync.app
    ├─ 4. Trim: googleapiclient discovery documents (keep ONLY drive.v3.json — the
    │       discovery_cache package must stay, build() imports it), QML, FFmpeg,
    │       translations, Tcl/Tk
    ├─ 5. Self test: dist/LarkSync.app/Contents/MacOS/LarkSync --selftest
    ├─ 6. codesign: ad-hoc by default; CODESIGN_IDENTITY → Developer ID + hardened
    │       runtime + installer/macos/entitlements.plist
    └─ 7. dmgbuild → dist/LarkSync.dmg (hdiutil fallback); with NOTARY_PROFILE the
            dmg is notarized and stapled
```

`setup.py` reads the version from `app/version.py`. It keeps `LSUIElement: False` (Dock icon + native menu bar), sets `LSMinimumSystemVersion 12.0` and bundles `assets/`.

### Windows build

`python build_windows.py` (also called by `build_windows.cmd` and CI):

```
PyInstaller --windowed --noconfirm --clean main.py
    --add-data assets;assets                       (os.pathsep-aware)
    --add-data …/drive.v3.json;googleapiclient/discovery_cache/documents
    --collect-submodules app / sync
    --icon assets/icon.ico  --version-file build/version_info.txt   (Windows only)
→ dist/LarkSync/LarkSync.exe  +  dist/LarkSync-<version>-Windows.zip         (--onedir)
→ dist/LarkSync-<version>-Portable.exe                                       (--onefile, same options)
iscc /DMyAppVersion=<version> installer/windows/LarkSync.iss
→ dist/LarkSync-Setup-<version>.exe
```

### CI (`.github/workflows/build.yml`)

| Job | Runs on | What |
|---|---|---|
| `test` | ubuntu, macOS, Windows | `pyflakes` + `pytest` (offscreen Qt). The suite includes real LaunchAgent / registry round-trips on their own OS |
| `build-macos` | macos-14 (Apple Silicon) | `build.sh` (includes `--selftest` of the `.app`), `hdiutil verify`, `codesign --verify`; uploads `LarkSync.dmg` |
| `build-windows` | windows-latest | `build_windows.py` (folder + portable), `--selftest` of both `.exe`s, Inno Setup; uploads Setup.exe + portable `.exe` + zip |
| `release` | tags `v*` only | Creates a **draft** GitHub release with the artifacts |

### Branch strategy

Work happens on short-lived branches merged into `main` by pull request; both platforms are built and tested from the same tree on every push, so there are no separate `macos` / `windows` branches any more (their features were already merged into `main`).

### Releasing

1. Bump `app/version.py` and add a `CHANGELOG.md` entry.
2. Merge to `main`, then `git tag v1.1.0 && git push origin v1.1.0`.
3. Review and publish the draft release created by CI.
