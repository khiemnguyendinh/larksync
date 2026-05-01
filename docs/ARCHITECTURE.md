# LarkSync — Architecture Reference

> **Audience:** Developers working on LarkSync source code.  
> **Last updated:** 2026-05-01

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
│  Data dir: ~/Documents/lark_gdrive_sync/                            │
│    app_config.json   lark_token.json   google_token.pkl             │
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
| CI/CD         | GitHub Actions (`build-windows.yml`)           |

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
└─────────────────────────┬───────────────────────────────────┘
                          │ reads/writes
┌─────────────────────────▼───────────────────────────────────┐
│                    APPLICATION LAYER                        │
│                                                             │
│  ConfigManager            SyncThread                        │
│  (config_manager.py)      (sync_thread.py)                  │
│  - app_config.json        - QThread subclass                │
│  - launch-at-login        - lock file management            │
│  - is_configured()        - emits progress/finished/error   │
└─────────────────────────┬───────────────────────────────────┘
                          │ drives
┌─────────────────────────▼───────────────────────────────────┐
│                       SYNC LAYER                            │
│                                                             │
│  SyncEngine          LarkClient         GoogleDriveClient   │
│  (sync_engine.py)    (lark_client.py)   (google_client.py)  │
│                                                             │
│  LarkAuth            LarkNotifier                           │
│  (lark_auth.py)      (lark_notifier.py)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Module Reference

### `main.py` — Entry point

| Responsibility | Details |
|---|---|
| Single-instance guard | Reads `LOCK_FILE`; if a living PID is found → show message and exit |
| First-run detection | If `config.is_first_run()` or credentials missing → open `SetupWizard` |
| Application subclass | `LarkSyncApp(QApplication)` intercepts macOS Dock-click to re-open Settings |
| Startup | Creates `ConfigManager` → `TrayApp` → `build_menu_bar()` (macOS only) |

---

### `app/config_manager.py` — Configuration persistence

**Data directory:** `~/Documents/lark_gdrive_sync/`  
**Config file:** `app_config.json`

| Symbol | Type | Purpose |
|---|---|---|
| `APP_DIR` | `Path` | Base directory for all user data |
| `CONFIG_FILE` | `Path` | Main config JSON |
| `LOG_FILE` | `Path` | `sync.log` — appended each sync run |
| `STATE_FILE` | `Path` | `sync_state.json` — Lark token → GDrive ID mapping |
| `LARK_TOKEN` | `Path` | Lark user OAuth token (JSON) |
| `GOOGLE_TOKEN` | `Path` | Google OAuth token (pickle) |
| `GOOGLE_CREDS` | `Path` | Google OAuth client credentials JSON |
| `LOCK_FILE` | `Path` | `~/.larksync.lock` — prevents concurrent syncs |

`ConfigManager` wraps a dict with `get()` / `set()` / `update()`. Every write immediately calls `_save()` → JSON file.

**Launch at login:**
- macOS: writes a `LaunchAgent` plist to `~/Library/LaunchAgents/com.larksync.agent.plist`
- Windows: writes to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`

---

### `app/tray_app.py` — System tray / menu bar

`TrayApp(QObject)` is the central controller of the running application.

**Key responsibilities:**

| Method | Purpose |
|---|---|
| `_build_menu()` | Constructs the QMenu each time state changes |
| `_refresh_menu()` | Rebuilds menu + updates tray icon |
| `_start_sync()` | Creates `SyncThread`, connects signals, starts it |
| `_cancel_sync()` | Calls `SyncThread.cancel()` |
| `_check_schedule()` | Called by 60-second `QTimer`; decides whether to auto-start sync |
| `_on_tray_clicked()` | **Toggle**: shows menu on first click, hides on second click |
| `_open_settings()` | **Singleton guard**: raises existing dialog if open, otherwise creates one |
| `_make_icon()` | Draws sync icon as Retina-scaled template image (macOS dark/light-mode safe) |

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

**Scheduler logic** (`_check_schedule()`):
- Reads `config.schedule` → `weekly` | `daily` | `manual`
- Compares `datetime.now()` against `last_sync` and target time
- Never fires on first launch (no `last_sync` recorded)
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
  Cancel: dimmed/disabled
  Sync Now: enabled (blue)

[User edits any field]
  Cancel: enabled (can revert by closing)
  Sync Now: enabled

[Sync Now clicked]
  Cancel: dimmed (disabled during sync)
  Sync Now → "Cancel Sync" (red)
  Status label: "⏳ Syncing…"
  _watch_sync_done() polls every 1s

[Sync completes]
  Sync Now restored (blue)
  Status label: "✓ Sync complete"

[Cancel Sync clicked during sync]
  Calls tray_app._cancel_sync()
  Restores button
```

---

### `app/sync_thread.py` — Background sync worker

`SyncThread(QThread)` runs the entire sync job off the main thread.

**Signals:**

| Signal | Type | Emitted when |
|---|---|---|
| `progress` | `str` | Each file processed (log line) |
| `file_done` | `(int, int)` | `(completed, total)` |
| `finished` | `dict` | Sync complete — stats dict |
| `error` | `str` | Fatal error — message string |

**Lock file protocol:**
1. On start: reads `LOCK_FILE`; if present checks if the PID is alive
2. If alive → emit `error("Another sync is already running.")`; return
3. If stale → remove lock; proceed
4. Writes own PID to lock; runs sync
5. `finally`: removes lock; emits `finished`

**After sync completes (in `finally`):**
- Saves `last_sync` and `last_sync_stats` to config
- Sends Lark group notification if `lark_notify_chat_id` is configured

---

### `sync/lark_auth.py` — Lark OAuth

Two distinct token types:

| Token | Function | Used by |
|---|---|---|
| `user_access_token` | Scoped `drive:drive:readonly` — user's personal Drive | `LarkClient` (Drive read) |
| `app_access_token` | App-level tenant token | `LarkNotifier` (send messages) |

**OAuth flow (`authorize()`):**
1. Starts a local `HTTPServer` on `localhost:8080`
2. Opens browser to Lark authorization URL
3. Receives `?code=…` callback
4. Exchanges code for tokens via `/authen/v1/oidc/access_token`
5. Saves token to `lark_token.json`

**Auto-refresh (`get_valid_access_token()`):**
- Checks `obtained_at + expire_in - 300` (5-min buffer)
- Calls `_refresh_token()` if within buffer
- Raises `RuntimeError` if no token exists (user must re-authorize)

---

### `sync/lark_client.py` — Lark Drive API

| Method | API endpoint | Notes |
|---|---|---|
| `list_folder(token)` | `GET /drive/v1/files` | Paginated (200/page) |
| `traverse(token, path)` | recursive DFS via `list_folder` | Returns flat list with `.path` and `.parent_token` |
| `export_native_file(token, type)` | `POST /drive/v1/export_tasks` then poll + download | 3-step async export |
| `download_file(token)` | `GET /drive/v1/files/{token}/download` | Regular (non-native) files |

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

Uses Google OAuth 2.0 with `drive` scope (read + write). Token stored as pickle at `google_token.pkl`.

| Method | API call | Notes |
|---|---|---|
| `get_or_create_folder(name, parent)` | `files.list` → `files.create` | Idempotent — won't create duplicates |
| `find_item(name, parent, is_folder)` | `files.list` with `q=` filter | Escapes single-quotes in names |
| `upload_file(content, filename, ext, parent, existing_id)` | `files.create` or `files.update` | If `existing_id` → overwrite; if ext is docx/xlsx/pptx → set `mimeType` to Google native format for in-Drive editing |

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
1. Call `lark.traverse("")` → flat list of all items
2. For each item:
   - If `type == "folder"` → `_sync_folder()` (always, to preserve structure)
   - If file:
     - Incremental mode: skip if `modified_time` / `created_time` ≤ `last_sync_ts`
     - Full mode: always sync
3. `_sync_file()`: download/export → `gdrive.upload_file()`
4. Save state

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

- **File menu**: Settings (⌘,) + Quit LarkSync (⌘Q)
- **Help menu**: Links to Lark app creation, Google API credentials, finding Lark Chat ID + About dialog

`_open_settings()` delegates to `tray_app._open_settings()` to share the singleton guard.

---

### `app/setup_wizard.py` — First-run Setup Wizard

A multi-page `QDialog` shown only on first launch or when credentials are missing. Guides the user through:

1. Lark App ID + Secret input
2. Google `credentials.json` upload + OAuth flow
3. Google Drive folder ID + optional Lark Chat ID
4. Schedule selection

---

## 4. Application Startup Sequence

```
main.py::main()
    │
    ├─ 1. Check LOCK_FILE (single-instance guard)
    │       If another instance running → show message → exit
    │
    ├─ 2. ConfigManager() → reads app_config.json
    │
    ├─ 3. is_first_run() or not is_fully_configured()?
    │    ├─ YES → SetupWizard().exec()
    │    │         If rejected → sys.exit(0)
    │    └─ NO  → continue
    │
    ├─ 4. TrayApp(config, app)
    │       ├─ Creates QSystemTrayIcon + QMenu
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
    ├─ _acquire_lock()
    │   Check ~/.larksync.lock
    │   If another process alive → emit error, return
    │   Write own PID to lock
    │
    ├─ _setup_logging()
    │   Configure FileHandler → ~/Documents/lark_gdrive_sync/sync.log
    │
    ├─ get_valid_access_token()    [auto-refresh if needed]
    │
    ├─ LarkClient(app_id, app_secret)
    ├─ GoogleDriveClient(creds_path, token_path)
    │
    ├─ SyncEngine.run()
    │   ├─ lark.traverse("") → flat list of all Lark items
    │   │
    │   └─ for each item:
    │       ├─ is folder → _sync_folder()
    │       │   └─ gdrive.get_or_create_folder() → save to state
    │       │
    │       └─ is file:
    │           ├─ [incremental] skip if not modified since last sync
    │           ├─ lark native? → export_native_file() [3-step async]
    │           ├─ regular?     → download_file()
    │           ├─ .url file?   → _resolve_url_file() → export
    │           └─ gdrive.upload_file() [create or overwrite]
    │               └─ save file token → GDrive ID to state
    │
    ├─ [finally] _release_lock()
    ├─ [finally] config.update({last_sync, last_sync_stats})
    ├─ [finally] emit finished(stats)
    │
    └─ _send_lark_notification(stats)
         LarkNotifier.notify_success() or notify_error()
         POST /im/v1/messages
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

finished(dict)         ──────────────► _on_finished(stats)
                                         _refresh_menu()
                                         showMessage(balloon notification)
                                         setToolTip("LarkSync")

error(str)             ──────────────► _on_error(msg)
                                         showMessage(error balloon)
```

PyQt6 signals are thread-safe for cross-thread connections — Qt queues them on the receiver's event loop automatically.

`SettingsDialog._watch_sync_done()` polls `tray_app._syncing` every 1 second via `QTimer.singleShot` (single-shot chain) to restore the "Sync Now" button after the sync completes.

---

## 7. Data Storage Schema

All user data lives in **`~/Documents/lark_gdrive_sync/`**. Nothing is stored inside the app bundle.

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
  "last_sync_stats":       {"folders": 5, "files_synced": 42, "errors": 0}
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

### `google_token.pkl`

Python-pickled `google.oauth2.credentials.Credentials` object. Managed automatically by `google-auth-oauthlib`.

---

## 8. Authentication Flows

### 8.1 Lark User OAuth (initial authorization)

```
Setup Wizard / "Re-authorize Lark" button
    │
    ▼
lark_auth.authorize()
    │
    ├─ Start HTTPServer on localhost:8080 (daemon thread)
    │
    ├─ Open browser:
    │   https://open.larksuite.com/open-apis/authen/v1/authorize
    │     ?app_id=cli_xxx&redirect_uri=http://localhost:8080/callback
    │     &scope=drive:drive:readonly&state=lark_sync
    │
    ├─ User logs in → Lark redirects to localhost:8080/callback?code=xxx
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
"Authenticate with Google" / "Re-authorize Google" button
    │
    ▼
GoogleDriveClient.get_service()
    └─ _get_credentials()
        ├─ Load google_token.pkl if exists
        ├─ If valid → use it
        ├─ If expired + has refresh_token → creds.refresh(Request())
        └─ Else: InstalledAppFlow.run_local_server(port=0)
                 Opens browser → user authorizes → code callback
                 Saves fresh token to google_token.pkl
```

---

## 9. Platform-Specific Code

### macOS

| Module | Mac-specific behavior |
|---|---|
| `mac_menu_bar.py` | `QMenuBar(None)` → global app menu bar; `QKeySequence("Ctrl+,")` → ⌘, on macOS |
| `tray_app.py::_make_icon()` | 36×36 Retina pixmap (18pt @2x); `setIsMask(True)` marks as template image — macOS inverts automatically in dark menu bar |
| `tray_app.py::_on_tray_clicked()` | Handles `Trigger` activation reason for left-click; toggles menu |
| `config_manager.py::set_launch_at_login()` | LaunchAgent plist → `~/Library/LaunchAgents/com.larksync.agent.plist` |
| `main.py::LarkSyncApp.event()` | Intercepts `ApplicationActivate` to re-open Settings on Dock click |
| `win_menu.py` | Excluded on macOS (`if sys.platform != "darwin"` guards in `tray_app.py`) |
| `setup.py` | `py2app` configuration — sets `CFBundleIdentifier`, `NSHighResolutionCapable`, `Info.plist` entries |

### Windows

| Module | Windows-specific behavior |
|---|---|
| `win_menu.py` | Provides an About dialog (macOS uses native Help menu) |
| `config_manager.py::set_launch_at_login()` | Writes to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| `build_windows.py` | `PyInstaller` spec — `--windowed`, `--icon`, `--add-data` for sync/ and app/ |
| `main.py` | `build_menu_bar` stub returns `None`; `_open_settings` stub opens dialog directly |
| `requirements_windows.txt` | Same packages minus `py2app` + `dmgbuild`; includes `pyinstaller` |

### Conditional imports pattern

```python
import sys

if sys.platform == "darwin":
    from app.mac_menu_bar import build_menu_bar, _open_settings
else:
    def build_menu_bar(config, tray_app):
        return None
    def _open_settings(config, tray_app):
        ...
```

Platform detection uses `sys.platform` (`"darwin"` / `"win32"`), never host-name or environment variables.

---

## 10. Build Pipeline

### macOS build (`bash build.sh`)

```
build.sh
    │
    ├─ 1. pip install dependencies (including py2app, dmgbuild)
    ├─ 2. Prepare icon: sips → icon.iconset → iconutil → icon.icns
    ├─ 3. python setup.py py2app
    │       → dist/LarkSync.app (py2app bundles Python + all deps)
    ├─ 4. Replace bundle icon with user's icon_1024.png
    ├─ 5. Post-build trim: remove test files, unused locales, .pyc cache
    │       (~407 MB → ~243 MB)
    └─ 6. dmgbuild → dist/LarkSync.dmg (~80 MB)
         Custom background + drag-to-Applications layout
```

`setup.py` key settings:
```python
OPTIONS = {
    "argv_emulation": False,       # prevent macOS argv injection
    "iconfile":       "assets/icon.icns",
    "plist": {
        "CFBundleIdentifier":      "com.kstudy.larksync",
        "NSHighResolutionCapable": True,
        "LSUIElement":             True,   # hide from Dock by default
        "CFBundleShortVersionString": "1.0.0",
    },
    "packages": ["sync", "app", "PyQt6", "google", ...],
}
```

### Windows build (CI via GitHub Actions)

`.github/workflows/build-windows.yml` triggers on push to `windows` branch:

```
GitHub Actions (Windows runner)
    │
    ├─ python -m pip install -r requirements_windows.txt
    ├─ python build_windows.py          ← PyInstaller spec
    │   → dist/LarkSync/LarkSync.exe
    └─ Upload artifact: LarkSync-Windows.zip
```

### Branch strategy

| Branch | Purpose | Build |
|---|---|---|
| `macos` | macOS development | Manual: `bash build.sh` |
| `windows` | Windows development | Auto: GitHub Actions on push |
| `main` | Stable merges | N/A |

New features should be developed on the appropriate platform branch, then a PR opened to merge into `main`. Features affecting both platforms should be cherry-picked between `macos` and `windows`.
