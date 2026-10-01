# LarkSync — Developer Guide

> **Audience:** Contributors and developers working on LarkSync.  
> **Last updated:** 2026-05-01  
> See [ARCHITECTURE.md](ARCHITECTURE.md) for module-level design documentation.

---

## Table of Contents

1. [Development Environment Setup](#1-development-environment-setup)
2. [Project Structure](#2-project-structure)
3. [Branch & Workflow Strategy](#3-branch--workflow-strategy)
4. [Running in Development Mode](#4-running-in-development-mode)
5. [Key Design Patterns](#5-key-design-patterns)
6. [How to Add a New Settings Field](#6-how-to-add-a-new-settings-field)
7. [How to Add a New Lark File Type](#7-how-to-add-a-new-lark-file-type)
8. [Platform Development Notes](#8-platform-development-notes)
9. [Building a Release](#9-building-a-release)
10. [Common Pitfalls & Known Issues](#10-common-pitfalls--known-issues)
11. [Code Style & Conventions](#11-code-style--conventions)

---

## 1. Development Environment Setup

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | 3.13 confirmed working for production builds |
| pip | latest | `pip install --upgrade pip` |
| Git | any recent | 2.x |
| macOS (for macOS branch) | 12+ | Apple Silicon or Intel |
| Windows (for windows branch) | 10/11 | Or use GitHub Actions |

### macOS setup

```bash
# 1. Clone the repository
git clone https://github.com/khiemnguyendinh/larksync.git
cd larksync

# 2. Create a virtual environment (recommended but not required)
python3 -m venv venv
source venv/bin/activate

# 3. Install the dependencies (runtime + test tools)
pip install -r requirements-dev.txt

# 4. Run the app in development mode
python main.py

# 5. Run the tests
python -m pytest tests -q
```

To build the app bundle you additionally need `requirements_macos.txt` (py2app, dmgbuild) — `bash build.sh` installs it into its own venv.

### Windows setup

```powershell
git clone https://github.com/khiemnguyendinh/larksync.git
cd larksync

python -m venv venv
venv\Scripts\activate

pip install -r requirements_windows.txt     # runtime + PyInstaller
pip install -r requirements-dev.txt         # + pytest / pyflakes

python main.py
python -m pytest tests -q
```

### IDE recommendations

**PyCharm** or **VS Code** with the Python extension. Mark `app/` and `sync/` as source roots so auto-import and go-to-definition work correctly.

---

## 2. Project Structure

```
larksync/
│
├── main.py                    # Entry point — startup sequence
│
├── app/                       # UI + application layer
│   ├── __init__.py
│   ├── version.py             # __version__ — single source of truth
│   ├── config_manager.py      # Config R/W (atomic), path constants, launch-at-login facade
│   ├── autostart.py           # LaunchAgent (macOS) / Run key (Windows)
│   ├── scheduler.py           # Pure schedule maths (catch-up, back-off)
│   ├── platform_utils.py      # IS_MAC / IS_WIN, resource_path(), Windows AppUserModelID
│   ├── tray_app.py            # Tray icon, menu, scheduler wiring, sync control
│   ├── settings_dialog.py     # Tabbed settings window + _SecretField widget
│   ├── setup_wizard.py        # First-run 4-step wizard
│   ├── sync_thread.py         # QThread wrapper for the sync engine
│   ├── oauth_worker.py        # QThreads for the Lark / Google browser sign-in
│   ├── log_viewer.py          # In-app log viewer dialog
│   ├── about_dialog.py        # Shared About dialog
│   ├── mac_menu_bar.py        # macOS native application menu bar [macOS only]
│   └── win_menu.py            # Windows About wrapper [Windows only]
│
├── sync/                      # Sync engine (no UI dependencies)
│   ├── __init__.py
│   ├── paths.py               # Data folder per OS, atomic write_private(), legacy migration
│   ├── lark_auth.py           # Lark OAuth flow + token management
│   ├── lark_client.py         # Lark Drive API (list, traverse, export, download, retry)
│   ├── google_client.py       # Google Drive API (folder, upload, overwrite, JSON token)
│   ├── sync_engine.py         # Core mirror logic (traverse → upload)
│   └── lark_notifier.py       # Post-sync Lark group chat notification
│
├── tests/                     # pytest suite (headless Qt) — see section 12
│
├── installer/
│   ├── macos/entitlements.plist   # Hardened-runtime entitlements for Developer-ID signing
│   └── windows/LarkSync.iss       # Inno Setup per-user installer
│
├── assets/
│   ├── icon.icns              # macOS icon (committed)
│   ├── icon.png               # 512 px master used for windows / tray / --selftest
│   └── icon.ico               # Windows icon (16–256 px, generated from icon.icns)
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System design + module reference
│   ├── DEVELOPER_GUIDE.md     # This file
│   ├── USER_GUIDE.md          # End-user guide (EN + VI)
│   ├── TERMS_OF_USE.md        # Terms of service
│   └── DISCLAIMER.md          # Liability disclaimer
│
├── .github/workflows/build.yml  # CI: tests (3 OSes) → macOS + Windows builds → draft release on v* tags
│
├── setup.py                   # py2app config (macOS build)
├── build.sh                   # macOS build script (produces .app + .dmg)
├── build_windows.py           # PyInstaller build (Windows) — used locally and by CI
├── build_windows.cmd          # Windows convenience wrapper
├── requirements.txt           # Runtime dependencies
├── requirements_macos.txt     # + py2app, dmgbuild
├── requirements_windows.txt   # + pyinstaller
├── requirements-dev.txt       # + pytest, pyflakes
├── CHANGELOG.md
└── README.md                  # Project overview
```

---

## 3. Branch & Workflow Strategy

`main` is the only long-lived branch. Work on a short-lived branch and open a pull request; CI (`build.yml`) runs the tests on Linux, macOS and Windows and builds both installers for every push, so a change that only works on one OS is caught before merge. (The former `macos` / `windows` branches were merged into `main`; the per-platform cherry-pick workflow is no longer needed.)

### Where platform-specific code lives

| Concern | Module |
|---|---|
| macOS native menu bar, Dock re-open | `app/mac_menu_bar.py`, `main.py::LarkSyncApp` |
| Launch at login | `app/autostart.py` (both OSes) |
| Tray behaviour / icon | `app/tray_app.py` (branches on `IS_MAC`) |
| Data folder | `sync/paths.py` |
| macOS packaging | `setup.py`, `build.sh`, `installer/macos/` |
| Windows packaging | `build_windows.py`, `build_windows.cmd`, `installer/windows/` |

Everything else is shared. Prefer `from app.platform_utils import IS_MAC, IS_WIN` over `sys.platform` checks scattered around — the flags can be monkeypatched, which is how the tests cover both code paths on one machine.

> **You cannot fully test a tray app headlessly.** The suite verifies logic and wiring for both platforms, and CI proves the bundles build and pass `--selftest`, but look at the real tray/menu bar on a real Mac and a real Windows PC before a release (checklist in section 9).

---

## 4. Running in Development Mode

```bash
python main.py
```

On first run, the Setup Wizard appears. After completing it, the tray icon appears in the menu bar.

### Skipping the wizard during development

If you've already completed setup once, the config is saved in the data folder (`~/Library/Application Support/LarkSync/app_config.json` on macOS, `%APPDATA%\LarkSync\app_config.json` on Windows). Point the app at a scratch folder with `LARKSYNC_HOME` to develop without touching your real data. To force the wizard to appear again:

```bash
# Method 1: Delete the config file
rm ~/Library/Application\ Support/LarkSync/app_config.json

# Method 2: Set first_run to true in the JSON
# Edit app_config.json and set "first_run": true
```

### Clearing Python bytecode cache

If you're seeing stale code running after edits (especially after `git checkout` or `git cherry-pick`):

```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

### Viewing the sync log

```bash
tail -f ~/Library/Application\ Support/LarkSync/sync.log     # Windows: Get-Content $env:APPDATA\LarkSync\sync.log -Wait
```

### Resetting all state (full clean slate)

```bash
rm -rf ~/Library/Application\ Support/LarkSync/     # Windows: rmdir /s /q %APPDATA%\LarkSync
# (v1.0.x data, if you still have it: ~/Documents/lark_gdrive_sync — it is copied over once, then left alone)
```

---

## 5. Key Design Patterns

### 5.1 QThread for background work

The sync job runs entirely in `SyncThread(QThread)`. **Never** do network I/O on the main thread — PyQt6 will freeze the UI.

Signal connections between threads are automatically queued by Qt (thread-safe). Always use `pyqtSignal` to communicate back to the main thread:

```python
class SyncThread(QThread):
    progress = pyqtSignal(str)    # Qt queues this for main-thread delivery
    finished = pyqtSignal(dict)

    def run(self):
        # This runs in a background thread
        self.progress.emit("Processing file X")
        self.finished.emit(stats)
```

### 5.2 Non-widget QObject as controller

`TrayApp` inherits `QObject` (not `QWidget`) because it's a controller that owns Qt objects but doesn't display itself. **Never** pass a `QObject`-but-not-`QWidget` as the Qt parent of a `QDialog` — this causes a `TypeError`. Always use `parent=None` for dialogs:

```python
# ✓ CORRECT
dlg = SettingsDialog(self.config, tray_app=self)  # tray_app as keyword, NOT Qt parent
dlg.exec()

# ✗ WRONG — will crash with TypeError
dlg = SettingsDialog(config, parent=self)  # self is not a QWidget!
```

### 5.3 Settings dialog singleton

Only one `SettingsDialog` can exist at a time. The guard lives in `TrayApp._open_settings()`:

```python
def _open_settings(self):
    if self._settings_dlg is not None and self._settings_dlg.isVisible():
        self._settings_dlg.raise_()
        self._settings_dlg.activateWindow()
        return
    self._settings_dlg = SettingsDialog(self.config, tray_app=self)
    self._settings_dlg.exec()   # blocks in nested event loop
    self._settings_dlg = None
    self._refresh_menu()
```

Any code path that opens Settings **must** call `tray_app._open_settings()`, not construct a `SettingsDialog` directly.

### 5.4 Secure input fields (`_SecretField`)

All sensitive credential fields use `_SecretField` (defined in `settings_dialog.py`). This is a `QWidget` subclass that wraps a password-mode `QLineEdit` + a 👁 eye toggle button.

`_SecretField` exposes the same `.text()`, `.setText()`, and `.textChanged` API as `QLineEdit`:

```python
field = _SecretField("placeholder")
field.setText("some_value")
value = field.text()
field.textChanged.connect(my_callback)  # proxied to inner QLineEdit
```

### 5.5 Incremental sync timestamp normalization

Lark API timestamps are returned inconsistently (sometimes `int`, sometimes `str`). Always normalize:

```python
def _ts(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
```

If a timestamp is missing or zero, the file is synced anyway (safe default).

### 5.6 Lock protocol

Two `QLockFile`s in the data folder (`QLockFile` stores the owner's PID and treats the lock as stale as soon as that process is gone, on every OS):

- `instance.lock` — held by `main.py` for the lifetime of the app (single instance)
- `sync.lock` — held by `SyncThread` while a sync runs

Never call `os.kill(pid, 0)` to test whether a process is alive: on Windows `os.kill` with any signal other than `CTRL_C_EVENT` / `CTRL_BREAK_EVENT` calls `TerminateProcess` — v1.0.x's single-instance check killed the running copy (and could kill an unrelated process that had reused the PID).

### 5.7 Never block the UI thread, never touch Qt from a plain thread

- Browser sign-ins (`authorize()`, `run_local_server`) block for minutes → use `app/oauth_worker.py` (QThreads + signals).
- `QTimer.singleShot(0, fn)` from a `threading.Thread` does **not** run `fn` (that thread has no event loop). Use a signal from a `QThread`.
- A `QThread` object must outlive its thread. Keep a reference until `finished`, and don't start a new one while `isRunning()`.
- Don't shadow Qt's built-in signals (`QThread.finished`); `SyncThread` uses `completed`.

### 5.8 Writing files that contain secrets

Use `sync.paths.write_private()` (atomic, `0600`) for anything holding the App Secret or tokens, and open credentials files with `encoding="utf-8"` (the Windows default code page can't read them).

---

## 6. How to Add a New Settings Field

This is the complete checklist for adding a new user-configurable setting:

### Step 1 — Add default to `config_manager.py`

```python
DEFAULTS: dict = {
    ...
    "my_new_setting": "default_value",   # ← add here
}
```

### Step 2 — Add UI widget to `settings_dialog.py`

In the appropriate tab method (e.g., `_general_tab()`):

```python
# Add the widget as an instance variable so _collect_updates() can read it
self._my_setting_edit = _input("Placeholder text")
self._my_setting_edit.setText(self.config.get("my_new_setting", ""))
layout.addWidget(self._my_setting_edit)
```

If the field is sensitive (API key, token, ID), use `_SecretField` instead of `_input`.

### Step 3 — Connect the change signal

In `_connect_change_signals()`:

```python
self._my_setting_edit.textChanged.connect(self._on_input_changed)
```

For a combo box: `self._my_combo.currentIndexChanged.connect(self._on_input_changed)`

### Step 4 — Include in `_collect_updates()`

```python
def _collect_updates(self) -> dict:
    return {
        ...
        "my_new_setting": self._my_setting_edit.text().strip(),
    }
```

### Step 5 — Use in `sync_thread.py` or wherever the setting applies

```python
my_value = self.config.get("my_new_setting", "default_value")
```

---

## 7. How to Add a New Lark File Type

To support a new Lark native file format (e.g., a hypothetical `"mindmap"` type):

### Step 1 — `sync/lark_client.py`

Add to `LARK_EXPORT_MAP`:
```python
LARK_EXPORT_MAP = {
    ...
    "mindmap": "pdf",   # new type → export as PDF
}
```
`LARK_NATIVE_TYPES` is derived automatically: `set(LARK_EXPORT_MAP.keys())`.

### Step 2 — Verify export API support

Check the Lark Open API docs to confirm `/drive/v1/export_tasks` supports the new type and what `file_extension` values it accepts.

### Step 3 — Test

The export path in `sync_engine.py` uses `LARK_NATIVE_TYPES` for the branch decision and `LARK_EXPORT_MAP` for the extension — no other changes needed.

---

## 8. Platform Development Notes

### macOS

**Menu bar icon template image:**

The tray icon is drawn as a Retina-scaled (18pt @ 2x = 36×36px) `QPixmap` with black strokes on transparent background. `icon.setIsMask(True)` marks it as a "template image" so macOS automatically inverts the icon to white in a dark menu bar.

```python
px = QPixmap(36, 36)
px.setDevicePixelRatio(2)   # 18pt @ 2x Retina
px.fill(Qt.GlobalColor.transparent)
# ... draw with QPainter using black strokes
icon = QIcon(px)
icon.setIsMask(True)
```

**Dark mode detection:**

```python
def _dark() -> bool:
    from PyQt6.QtWidgets import QApplication
    return QApplication.palette().window().color().lightness() < 128
```

Use `_c(light_value, dark_value)` helper in `settings_dialog.py` to pick the correct color for each mode.

**`QKeySequence("Ctrl+,")` on macOS:**

Qt automatically maps `Ctrl` → `⌘` on macOS. `"Ctrl+,"` becomes `⌘,` in the menu.

**`LSUIElement = False` in `setup.py`:**

LarkSync deliberately shows a Dock icon and the native menu bar (File / Help), plus the menu-bar extra. Clicking the Dock icon re-opens Settings (`LarkSyncApp.event`). Setting it to `True` would make it a pure menu-bar utility with no Dock icon and no native menu bar.

**Hardened runtime / notarization (untested here):** `build.sh` supports `CODESIGN_IDENTITY` and `NOTARY_PROFILE`; the entitlements live in `installer/macos/entitlements.plist`. Without a Developer-ID certificate the build is ad-hoc signed (required to run on Apple Silicon) and users must right-click → Open on first launch.

**Architecture:** `lipo -archs dist/LarkSync.app/Contents/MacOS/LarkSync` tells you what you built. CI builds on an Apple-Silicon runner (arm64); an Intel or universal2 build needs an Intel/universal2 Python.

**Data folder:** `~/Library/Application Support/LarkSync` (not `~/Documents`, which iCloud may sync).

### Windows

**Icons:** the exe icon is `assets/icon.ico` (multi-size, regenerate with Pillow from `assets/icon.icns`/`icon.png` if the artwork changes); windows and the tray use `assets/icon.png`. The tray glyph is drawn in code in brand blue/orange because a black "template" icon is invisible on the default dark taskbar.

**No native menu bar on Windows:** `build_menu_bar()` is macOS-only. Everything is reached through the tray menu: **right-click** shows it (`QSystemTrayIcon.setContextMenu`), **left-click / double-click** opens Settings. Don't call `QMenu.popup()` for tray menus on Windows — the menu then doesn't close when you click elsewhere.

**Taskbar / toast identity:** `set_windows_app_id()` sets an AppUserModelID so notifications read "LarkSync".

**`--windowed` has no stdout/stderr:** `sys.stderr` is `None`; don't add a `StreamHandler` blindly and don't `print()`.

**Registry launch-at-login:** `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` — no elevation needed. From source it launches `pythonw.exe main.py`; the installer's "start when I sign in" task writes the same value and the uninstaller removes it.

**OAuth callback port:** Lark's redirect URL is fixed to `http://localhost:8080/callback`. The loopback server deliberately does not set `SO_REUSEADDR` on Windows (it would let a second program share the port and hide conflicts).

**SmartScreen:** builds are unsigned. For a signed build use `signtool` (or Azure Trusted Signing) on `LarkSync.exe` before running Inno Setup, and on the installer afterwards.

---

## 9. Building a Release

### macOS (`bash build.sh`)

```bash
bash build.sh
# Outputs:
#   dist/LarkSync.app    (the app bundle, self-tested and signed)
#   dist/LarkSync.dmg    (the installer)

# Distributable build (needs an Apple Developer ID):
CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
NOTARY_PROFILE=my-notary-profile bash build.sh
```

The script uses the committed `assets/icon.icns` (set `ICON_SRC=/path/to/1024.png` to regenerate it), runs `LarkSync --selftest` on the finished bundle and fails the build if anything is missing.

### Windows

```powershell
python build_windows.py                      # dist\LarkSync\ + dist\LarkSync-<version>-Windows.zip
dist\LarkSync\LarkSync.exe --selftest        # exit code 0 = OK, details in %APPDATA%\LarkSync\selftest.txt
iscc /DMyAppVersion=1.1.0 installer\windows\LarkSync.iss     # dist\LarkSync-Setup-1.1.0.exe
```

### Through CI (recommended)

Every push builds both platforms (see `.github/workflows/build.yml`); download the artifacts from the run. Pushing a tag `vX.Y.Z` also creates a **draft** GitHub release with the `.dmg`, the Setup `.exe` and the `.zip`.

### Version bumping

Edit **one** place: `app/version.py` (`__version__`). `setup.py`, `build.sh`, `build_windows.py`, the Inno script (via `/DMyAppVersion`), the About dialog and the tray menu title all read it. Add a `CHANGELOG.md` entry, then tag `vX.Y.Z`.

### Pre-release checklist (needs real machines)

CI cannot see a real menu bar or taskbar. On a Mac **and** a Windows PC:

- [ ] Fresh install, run the Setup Wizard end to end (Lark + Google sign-in, window stays responsive)
- [ ] Tray/menu-bar icon visible in light **and** dark mode; menu opens/closes correctly
- [ ] Windows: right-click shows the menu, left-click opens Settings
- [ ] macOS: Dock-click re-opens Settings; ⌘R / ⌘, / ⌘Q work
- [ ] Sync Now → Cancel Sync → "Cancelling…" → cancelled notification; then a full sync
- [ ] Settings → Launch at Login on, log out/in, app starts (once); off removes it
- [ ] Upgrade from a v1.0.x profile: data migrated, schedule still works
- [ ] Quit during a sync does not crash

---

## 10. Common Pitfalls & Known Issues

### Stale `.pyc` bytecode after `git` operations

**Problem:** After `git cherry-pick`, `git checkout`, or `git rebase`, Python may keep running the old bytecode from `__pycache__`. This is the most common source of "my change isn't taking effect" confusion.

**Fix:**
```bash
find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; python main.py
```

### `TypeError: QWidget requires a QWidget parent`

**Problem:** Passing `TrayApp` (a `QObject`, not `QWidget`) as the Qt parent of a `QDialog`.

**Fix:** Always pass `tray_app` as a keyword argument, never as positional parent:
```python
dlg = SettingsDialog(config, tray_app=tray_app)  # correct
dlg = SomeDialog(tray_app)                         # wrong if tray_app is QObject
```

### Lark timestamp `TypeError: '<=' not supported between instances of 'str' and 'int'`

**Problem:** Lark API returns `modified_time`/`created_time` as strings in some cases and ints in others.

**Fix:** Always normalize with the `_ts()` helper in `sync_engine.py`. Never compare a raw Lark timestamp against a number.

### Lark notification 400 Bad Request

**Problem:** Using `get_valid_access_token()` (user OAuth token) for sending messages — the `drive:drive:readonly` scope doesn't allow messaging.

**Fix:** `SyncThread._send_lark_notification()` must use `get_app_access_token()` (app/tenant token), not the user token.

### py2app Python version

`py2app` bundles **whatever Python is invoked by `python3`** on your system. `build.sh` creates `.build-venv` from the `python3` on your PATH (3.11+ recommended), so check `python3 --version` first.

### Don't delete `googleapiclient/discovery_cache`

`googleapiclient.discovery.build()` imports that package at runtime. Delete only the (huge) `documents/` JSON files except `drive.v3.json`, as `build.sh` / `build_windows.py` do. `--selftest` fails the build if this goes wrong.

### Lock file from crash

If the app crashes, `instance.lock` / `sync.lock` may remain in the data folder. `QLockFile` detects that the owner process is gone and takes the lock over, so nothing needs deleting. If you ever have to: remove `instance.lock` and `sync.lock` from the data folder.

### Google OAuth token pickle incompatibility

v1.0.x stored `google_token.pkl` (a pickle, which breaks across Python upgrades). v1.1 stores `google_token.json` and migrates the pickle automatically; if a legacy pickle can't be read, the user is simply asked to re-authorize.

### Google sign-in expires every 7 days

An OAuth consent screen in **Testing** status expires refresh tokens after 7 days. The app reports `GoogleAuthRequired` ("Re-authorize Google"); publish the OAuth app to *In production* to avoid it.

---

## 11. Code Style & Conventions

### General

- **Python 3.11+** syntax; avoid walrus operator and match-case for wider compatibility
- **4-space indentation**; no tabs
- **Type hints** on function signatures where non-obvious
- **Docstrings** on all public classes and non-trivial methods

### Naming

| Entity | Convention | Example |
|---|---|---|
| Classes | `PascalCase` | `SyncThread`, `LarkClient` |
| Functions/methods | `snake_case` | `_sync_folder`, `get_access_token` |
| Private helpers | `_leading_underscore` | `_poll_export_task` |
| Module-level constants | `UPPER_SNAKE` | `LARK_BASE_URL`, `APP_DIR` |
| Signal names | `snake_case` | `progress`, `file_done` |

### Qt-specific conventions

- All UI construction happens in `__init__` or dedicated `_build_*()` methods
- Signals are connected **after** all widgets are built (avoids callbacks on partially initialized state)
- Widget factory functions (`_input()`, `_combo()`, `_label()`) are module-level utilities — keep them pure (no side effects)
- Platform-specific code is guarded with `IS_MAC` / `IS_WIN` from `app/platform_utils.py` (they wrap `sys.platform` and can be monkeypatched in tests)

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed trace info")
logger.info("[FOLDER] Created: /path → gDriveId")
logger.warning("Skipping large file: ...")
logger.exception("Sync crashed")   # includes full traceback
```

Never use `print()` in production code — it won't appear in the log file.

### Error handling

- **Network errors:** always `resp.raise_for_status()` followed by checking `data.get("code") != 0` for Lark API errors
- **Per-file errors:** caught in `SyncEngine.run()` loop, increment `stats["errors"]`, continue with next file — never abort the whole sync
- **Notification errors:** silently logged, never raised — notification failure must not affect sync result

### Commit message format

```
<type>: <short summary>

<optional body>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `build`

Example: `fix: normalize Lark timestamps to float before comparison`

---

## 12. Testing

```bash
python -m pytest tests -q          # ~120 tests, ~4 s, no network, no display needed
python -m pyflakes main.py app sync tests
```

`tests/conftest.py` points `LARKSYNC_HOME` at a temp folder **before** any LarkSync module is imported (paths are resolved at import time), empties it between tests and runs Qt with `QT_QPA_PLATFORM=offscreen`.

| File | Covers |
|---|---|
| `test_scheduler.py` | catch-up after a missed slot, re-arming, retry back-off, invalid values |
| `test_paths_config.py` | atomic/private writes, legacy-folder migration, per-OS data folder, corrupt config |
| `test_autostart.py` | LaunchAgent plist, Windows Run value / launch commands, enable/disable, the Settings regression |
| `test_sync_engine.py` | conflict skip/overwrite, incremental filter, errors, size limit, shortcuts, cancel + state save, `.url` files |
| `test_lark.py` | retry/back-off, pagination, cancellable traverse, download limit, the OAuth loopback flow (success, forged `state`, timeout frees the port, cancel, port in use), token refresh errors |
| `test_google.py` | overwrite → create fallback, `'root'` anchoring, JSON token + pickle migration, expired token → `GoogleAuthRequired`, no browser in background syncs |
| `test_sync_thread.py` | which marker moves for clean / errors / fatal / cancelled runs, lock contention, signal count |
| `test_tray.py` | Windows context menu + click handling, macOS toggle, icons, cancel state machine, scheduler wiring |
| `test_dialogs.py` | Save vs Sync Now, background sign-in, wizard validation, finish confirmation, OAuth workers |
| `test_platform_real.py` | real registry / LaunchAgent round-trips (each runs only on its own OS, in CI) |

The sync tests use fakes (`FakeLark`, `FakeDrive`); nothing talks to Lark or Google. When you fix a bug, add the regression test next to the code it covers — most of the tests above are named after a v1.0.x bug.

