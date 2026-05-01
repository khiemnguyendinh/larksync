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

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Run the app in development mode
python main.py
```

### Windows setup

```powershell
git clone https://github.com/khiemnguyendinh/larksync.git
cd larksync

python -m venv venv
venv\Scripts\activate

pip install -r requirements_windows.txt

python main.py
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
│   ├── config_manager.py      # Config R/W, launch-at-login, path constants
│   ├── tray_app.py            # Tray icon, menu, scheduler, sync control
│   ├── settings_dialog.py     # Tabbed settings window + _SecretField widget
│   ├── setup_wizard.py        # First-run 4-step wizard
│   ├── sync_thread.py         # QThread wrapper for sync engine
│   ├── log_viewer.py          # In-app log viewer dialog
│   ├── mac_menu_bar.py        # macOS native application menu bar [macOS only]
│   └── win_menu.py            # Windows About dialog [Windows only]
│
├── sync/                      # Sync engine (no UI dependencies)
│   ├── __init__.py
│   ├── lark_auth.py           # Lark OAuth flows + token management
│   ├── lark_client.py         # Lark Drive API (list, traverse, export, download)
│   ├── google_client.py       # Google Drive API (folder, upload, overwrite)
│   ├── sync_engine.py         # Core mirror logic (traverse → upload)
│   └── lark_notifier.py       # Post-sync Lark group chat notification
│
├── assets/                    # Icons and build assets
│   ├── icon_1024.png          # Source icon (generated from user's PNG at build time)
│   ├── icon.icns              # macOS icon bundle (generated at build time)
│   └── dmg_background.png    # DMG window background
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System design + module reference (this project)
│   ├── DEVELOPER_GUIDE.md     # This file
│   ├── USER_GUIDE.md          # End-user guide (EN + VI)
│   ├── TERMS_OF_USE.md        # Terms of service
│   └── DISCLAIMER.md         # Liability disclaimer
│
├── .github/
│   └── workflows/
│       └── build-windows.yml  # CI: auto-build Windows .exe on push to windows branch
│
├── setup.py                   # py2app config (macOS build)
├── build.sh                   # macOS build script (produces .app + .dmg)
├── build_windows.py           # PyInstaller spec (Windows)
├── build_windows.cmd          # Windows build script
├── requirements.txt           # macOS/Linux Python dependencies
├── requirements_windows.txt   # Windows Python dependencies
└── README.md                  # Project overview
```

---

## 3. Branch & Workflow Strategy

### Branch layout

```
main ──────────────────────────────────────────────────►
       ▲                        ▲
       │  merge PR              │  merge PR
macos ─┼────────────────────────┼──────────────────────►
       │  (macOS development)   │
windows─┼────────────────────────┼──────────────────────►
          (Windows development + CI build)
```

| Branch | Owner | CI |
|---|---|---|
| `macos` | macOS developer | Manual build with `bash build.sh` |
| `windows` | Windows developer (Antigravity) | GitHub Actions auto-builds `.exe` on every push |
| `main` | Both | Stable merged releases |

### Feature development workflow

1. Work on the relevant platform branch (`macos` or `windows`)
2. If a change applies to **both platforms** (e.g., shared logic in `sync/` or `app/config_manager.py`), cherry-pick the commit to the other branch:
   ```bash
   git checkout macos
   git cherry-pick <commit-hash-from-windows>
   git push origin macos
   ```
3. When a feature is complete and tested on both platforms, open a PR to merge into `main`.

### Cross-platform shared modules

Changes to these modules must be tested on **both platforms** and cherry-picked:
- `sync/` (entire package)
- `app/config_manager.py`
- `app/sync_thread.py`
- `app/settings_dialog.py` (UI shared between platforms)
- `app/setup_wizard.py`
- `app/log_viewer.py`
- `main.py`

Changes to these modules are **platform-exclusive**:
- `app/mac_menu_bar.py` — macOS only
- `app/win_menu.py` — Windows only
- `build.sh`, `setup.py` — macOS build only
- `build_windows.py`, `build_windows.cmd` — Windows build only
- `.github/workflows/` — CI/CD

---

## 4. Running in Development Mode

```bash
python main.py
```

On first run, the Setup Wizard appears. After completing it, the tray icon appears in the menu bar.

### Skipping the wizard during development

If you've already completed setup once, the config is saved in `~/Documents/lark_gdrive_sync/app_config.json`. To force the wizard to appear again:

```bash
# Method 1: Delete the config file
rm ~/Documents/lark_gdrive_sync/app_config.json

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
tail -f ~/Documents/lark_gdrive_sync/sync.log
```

### Resetting all state (full clean slate)

```bash
rm -rf ~/Documents/lark_gdrive_sync/
rm -f ~/.larksync.lock
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

### 5.6 Lock file protocol

`~/.larksync.lock` contains the PID of the running sync. On acquisition:
1. Check if file exists
2. If yes, read PID and call `os.kill(pid, 0)` — raises `ProcessLookupError` if dead
3. If dead (stale) → remove lock and proceed
4. Write own PID
5. `finally` block always removes the lock

This handles crashes gracefully — stale locks are automatically cleaned.

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

**`LSUIElement = True` in `setup.py`:**

This hides LarkSync from the Dock. Without it, a Dock icon appears even though the app is a menu-bar utility.

### Windows

**Tray icon `.png` vs `.ico`:**

PyInstaller needs a `.ico` file for the app icon. The `build_windows.py` script converts the PNG. Make sure any icon change is also applied to the Windows build.

**No native menu bar on Windows:**

`build_menu_bar()` returns `None` on Windows. The macOS `File` and `Help` menus don't exist. All access to Settings is through the tray icon's context menu.

**`QSystemTrayIcon.ActivationReason`:**

On Windows, right-click shows the context menu automatically. The `Trigger` reason fires on left-click and is used to manually show the popup. This is the same code path as macOS.

**Registry launch-at-login:**

Tested path: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Does NOT require elevation.

---

## 9. Building a Release

### macOS release

```bash
# Ensure you're on the macos branch
git checkout macos

# Place the 1024×1024 app icon on your Desktop as "larksync icon.png"
# (the build script reads from ~/Desktop/larksync icon.png)

# Run the build
bash build.sh

# Outputs:
#   dist/LarkSync.app    (the app bundle)
#   dist/LarkSync.dmg    (the installer, ~80 MB)
```

**Uploading a GitHub release:**

GitHub's web UI supports files up to 2 GB. Use the Releases page to attach the `.dmg`.

> The GitHub CLI (`gh release create`) requires `gh auth login` first.

### Windows release (GitHub Actions)

1. Push to the `windows` branch
2. GitHub Actions builds automatically
3. Artifacts are available on the Actions page under the workflow run
4. Download `LarkSync-Windows.zip` → contains `LarkSync.exe` and all dependencies

### Version bumping

Version numbers appear in:
- `build.sh`: `VERSION="1.0.0"`
- `setup.py`: `version="1.0.0"`
- `app/mac_menu_bar.py`: in `CREDIT_TEXT`
- `app/win_menu.py`: in the About dialog
- GitHub release tag: `v1.0.0`

Update all four locations before tagging a release.

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

`py2app` bundles **whatever Python is invoked by `python3`** on your system. If you're using a venv with Python 3.13 but `python3` on PATH points to 3.9 (common on older Macs), the bundle will contain 3.9 — which may not support newer syntax.

**Fix:** Always run `bash build.sh` from within a venv that uses the exact Python version you intend to bundle.

### Lock file from crash

If the app crashes mid-sync, `~/.larksync.lock` may remain. The next launch detects the stale lock (dead PID) and removes it automatically. If for some reason this doesn't work:
```bash
rm ~/.larksync.lock
```

### Google OAuth token pickle incompatibility

`google_token.pkl` is a Python pickle. If you change Python minor versions significantly, the pickle may fail to deserialize. Solution: delete `google_token.pkl` and re-authenticate via Settings → Google Drive → Re-authorize Google.

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
- Platform-specific code is guarded with `if sys.platform == "darwin":` / `"win32"`

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
