<div align="center">

# LarkSync

**Sync Lark Drive → Google Drive, automatically.**  
A lightweight desktop app for seamless file synchronization — available for **macOS** and **Windows**.

[![Platform - macOS](https://img.shields.io/badge/platform-macOS%2012%2B-lightgrey?logo=apple)](https://github.com/khiemnguyendinh/larksync/releases)
[![Platform - Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-blue?logo=windows)](https://github.com/khiemnguyendinh/larksync/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Release](https://img.shields.io/github/v/release/khiemnguyendinh/larksync?color=orange)](https://github.com/khiemnguyendinh/larksync/releases)
[![Version](https://img.shields.io/badge/version-1.1.0-informational)](CHANGELOG.md)
[![Build & Test](https://img.shields.io/github/actions/workflow/status/khiemnguyendinh/larksync/build.yml?branch=main&label=Build%20%26%20Test&logo=github)](https://github.com/khiemnguyendinh/larksync/actions/workflows/build.yml)
[![Author](https://img.shields.io/badge/author-Khiem%20Nguyen%20Dinh-purple)](https://www.kstudy.edu.vn)

</div>

---

## What's new in 1.1.0

- **Windows tray menu works** — right-click shows the menu (it did nothing before), the icon is visible on a dark taskbar, and starting a second copy no longer kills the first.
- **Missed schedules catch up** — if the Mac was asleep or the PC off at the scheduled time, the sync runs as soon as LarkSync is running again; failed runs retry with back-off.
- **No more silent data gaps** — a crashed or cancelled sync no longer moves the incremental marker, so files that never uploaded are retried.
- **Sign-in never freezes the window**, and Settings now has a real **Save** button.
- **Launch at Login actually works** on both OSes.
- **Secrets moved out of `~/Documents`** to the OS app-data folder (auto-migrated; see [CHANGELOG](CHANGELOG.md)).
- **macOS build fixed** (the Google API could fail inside the packaged app) and **Windows installer** (`Setup.exe`) added.

Full list and upgrade notes: **[CHANGELOG.md](CHANGELOG.md)**.

---

## Features

- **Cross-platform** — Available for both macOS and Windows
- **Automatic sync** — Schedule syncs daily, weekly, or run on demand
- **System tray integration** — Lives quietly in the macOS menu bar or Windows system tray
- **Lark Drive support** — Works with Lark (Feishu) custom app credentials
- **Google Drive upload** — Uploads to any target folder in your Google Drive via OAuth 2.0
- **Format conversion** — Lark-native files (Docs, Sheets, Mindnotes) exported to Google-compatible formats (Docx, Xlsx, PDF)
- **Incremental sync** — Only sync new and modified files since last run (faster)
- **Smart Settings UX** — Save, or Sync Now (saves + syncs); Cancel Sync mid-flight; singleton window guard
- **Secure credential fields** — All API keys and IDs hidden by default with a 👁 eye toggle
- **Setup Wizard** — Guided first-time configuration for both Lark and Google credentials
- **Sync log** — In-app log viewer for reviewing sync history and diagnosing errors
- **Lark group notification** — Get notified in your Lark group chat after each sync
- **Launch at login** — Auto-start via a macOS LaunchAgent or the Windows `Run` registry key
- **Catch-up scheduling** — Missed syncs run when the app is next running; failed runs retry with back-off
- **Shared Drives** — The destination folder can be in a Google Shared Drive
- **Lightweight** — Built with Python + PyQt6, packaged as `.app`/`.dmg` (macOS) or `.exe`/Setup (Windows)

---

## Requirements

### External Credentials (Required for all users)
- **Lark App** with Drive read permissions (App ID + App Secret) — [Create one here](https://open.larksuite.com/app)
- **Google Cloud project** with Drive API enabled (`credentials.json`) — [Set up here](https://console.cloud.google.com/apis/credentials)

### Pre-built App (Recommended)

| Platform | Requirements |
|----------|-------------|
| **macOS** | macOS 12 Monterey or later. The CI-built DMG targets Apple Silicon; Intel Macs: build from source |
| **Windows** | Windows 10 or later (64-bit) |

> No Python installation required for pre-built apps.

### Build from Source
- Python 3.11 or later
- pip / virtualenv (the macOS build script creates its own venv)

---

## 🍎 macOS — Quick Install

1. Download the latest `LarkSync.dmg` from [Releases](https://github.com/khiemnguyendinh/larksync/releases) (or from the latest green run of [Actions → Build & Test](https://github.com/khiemnguyendinh/larksync/actions/workflows/build.yml), artifact **LarkSync-macOS**).
2. Open the DMG and drag **LarkSync.app** to your **Applications** folder.
3. **First launch:** Right-click the app → **Open** → **Open** (bypasses Gatekeeper for apps that are not notarized).
4. The Setup Wizard will guide you through the rest.

> If macOS says the app is damaged, run: `xattr -cr /Applications/LarkSync.app`

---

## 🪟 Windows — Quick Install

1. Download **`LarkSync-Setup-<version>.exe`** from [Releases](https://github.com/khiemnguyendinh/larksync/releases) (or the **LarkSync-Windows** artifact of the latest green [Build & Test](https://github.com/khiemnguyendinh/larksync/actions/workflows/build.yml) run).
2. Run it — it installs for your user only, no administrator rights needed.
3. Start **LarkSync** from the Start menu; the Setup Wizard will guide you through the rest.
4. Prefer no installer? Use the single-file `LarkSync-<version>-Portable.exe` (just run it), or `LarkSync-<version>-Windows.zip` (extract and run `LarkSync.exe`).

> **Note:** The app lives in your system tray (near the clock — click **^** if hidden). **Right-click** the icon for the menu, **left-click** to open Settings. SmartScreen may warn about an unsigned app: **More info → Run anyway**. Details: [Windows guide](Windows_Readme.md).

---

## Quick Start

After installation, the Setup Wizard will ask for:

| Step | What You Need |
|------|---------------|
| Lark App credentials | App ID + App Secret from [open.larksuite.com/app](https://open.larksuite.com/app) |
| Google credentials | `credentials.json` from [console.cloud.google.com](https://console.cloud.google.com) |
| Google Drive Folder ID | From the Google Drive folder URL (optional) |
| Sync schedule | Manual, Daily, or Weekly |
| Lark notification | Group Chat ID (optional) |

See the full [User Guide](docs/USER_GUIDE.md) for step-by-step instructions.

---

## Build from Source

### macOS

```bash
# 1. Clone the repository
git clone https://github.com/khiemnguyendinh/larksync.git
cd larksync

# 2. Run in development mode
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py

# 3. Build the .app bundle + .dmg installer (creates its own venv)
bash build.sh
# Output: dist/LarkSync.app + dist/LarkSync.dmg
```

`build.sh` trims the bundle, runs `LarkSync --selftest` against it, and signs it (ad-hoc by default; set `CODESIGN_IDENTITY` / `NOTARY_PROFILE` for a notarized, distributable build — see the [Developer Guide](docs/DEVELOPER_GUIDE.md#9-building-a-release)).

### Windows

```powershell
# 1. Clone the repository
git clone https://github.com/khiemnguyendinh/larksync.git
cd larksync

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements_windows.txt

# 4. Run in development mode
python main.py

# 5. Build the .exe files (PyInstaller): folder + zip, and a portable single file
build_windows.cmd
# Output: dist\LarkSync\LarkSync.exe, dist\LarkSync-<version>-Portable.exe

# 6. Optional: the Setup.exe installer (Inno Setup 6.3+)
iscc /DMyAppVersion=1.1.0 installer\windows\LarkSync.iss
```

> **Tip:** You don't need a Windows machine or a Mac to get the installers! The GitHub Actions workflow ([`build.yml`](.github/workflows/build.yml)) runs the tests on Linux, macOS and Windows and builds both installers on every push; pushing a `v*` tag also drafts a GitHub release.

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q        # ~120 tests, headless, no network
```

**Dependencies:**
- `PyQt6` — Cross-platform UI framework
- `google-api-python-client` — Google Drive API
- `google-auth-oauthlib` — Google OAuth flow
- `requests` — HTTP client for Lark API
- `py2app` / `dmgbuild` — macOS bundler (macOS build only)
- `pyinstaller` — Windows executable bundler (Windows build only)

---

## Project Structure

```
larksync/
├── main.py                  # App entry point (cross-platform; `--selftest` for CI)
├── app/                     # UI + application layer
│   ├── version.py           # Single source of truth for the version
│   ├── config_manager.py    # Config persistence (atomic, private)
│   ├── autostart.py         # Launch at login (LaunchAgent / Run key)
│   ├── scheduler.py         # Schedule maths: catch-up + retry back-off
│   ├── platform_utils.py    # IS_MAC / IS_WIN, resource lookup
│   ├── tray_app.py          # System tray / menu bar logic + scheduler wiring
│   ├── settings_dialog.py   # Tabbed settings window
│   ├── setup_wizard.py      # First-run 4-step wizard
│   ├── sync_thread.py       # Background sync QThread
│   ├── oauth_worker.py      # Non-blocking Lark / Google sign-in
│   ├── log_viewer.py        # Sync log viewer
│   ├── about_dialog.py      # Shared About dialog
│   ├── mac_menu_bar.py      # macOS native application menu bar
│   └── win_menu.py          # Windows About wrapper
├── sync/                    # Sync engine (no UI dependencies)
│   ├── paths.py             # Data folder per OS, atomic private writes, migration
│   ├── lark_auth.py         # Lark OAuth flow + token management
│   ├── lark_client.py       # Lark Drive API client
│   ├── google_client.py     # Google Drive API client
│   ├── sync_engine.py       # Core sync logic
│   └── lark_notifier.py     # Post-sync group chat notification
├── tests/                   # pytest suite
├── installer/               # macOS entitlements, Windows Inno Setup script
├── assets/                  # Icons (icns / png / ico)
├── docs/                    # Documentation
├── .github/workflows/       # CI/CD
│   └── build.yml            # Tests (3 OSes) + macOS + Windows builds + draft release
├── setup.py                 # py2app configuration (macOS)
├── build.sh                 # macOS build script (.app + .dmg)
├── build_windows.py         # PyInstaller build (Windows)
├── build_windows.cmd        # Windows build wrapper
├── requirements.txt         # Runtime dependencies
├── requirements_macos.txt   # + py2app, dmgbuild
├── requirements_windows.txt # + pyinstaller
├── requirements-dev.txt     # + pytest, pyflakes
└── CHANGELOG.md
```

Your data lives in `~/Library/Application Support/LarkSync` (macOS) or `%APPDATA%\LarkSync` (Windows).

---

## Branches

`main` is the only long-lived branch; work happens on short-lived branches merged by pull request. CI builds and tests both platforms from the same tree, so the old `macos` / `windows` branches are no longer needed.

---

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | End users | Installation, setup, and usage instructions (EN + VI) |
| [Architecture](docs/ARCHITECTURE.md) | Developers | System design, module reference, data flows, build pipeline |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Developers | Dev environment, patterns, how-to guides, pitfalls |
| [Terms of Use](docs/TERMS_OF_USE.md) | End users | Terms governing use of LarkSync (EN + VI) |
| [Disclaimer](docs/DISCLAIMER.md) | End users | Liability disclaimer and warranty information (EN + VI) |

---

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit: `git commit -m "Add: your feature description"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request

**Please:**
- Follow the existing code style
- Add or update tests (`python -m pytest tests`) — CI runs them on Linux, macOS and Windows
- Update documentation as needed
- Do not commit credentials or token files

For bugs, please open a [GitHub Issue](https://github.com/khiemnguyendinh/larksync/issues) with:
- Your OS (macOS / Windows) and version
- A description of the problem
- The relevant section of your sync log

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Credits & Acknowledgments

**Developer:** [Khiem Nguyen Dinh](https://www.kstudy.edu.vn) ([@khiemnguyendinh](https://github.com/khiemnguyendinh))  
**Organization:** [Kstudy Academy](https://www.kstudy.edu.vn)  
**Contact:** [khiem@kstudy.edu.vn](mailto:khiem@kstudy.edu.vn)

Built with:
- [Python](https://www.python.org/) & [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [Lark Open API](https://open.larksuite.com/)
- [Google Drive API](https://developers.google.com/drive)
- [py2app](https://py2app.readthedocs.io/) (macOS) & [PyInstaller](https://pyinstaller.org/) (Windows)

---

> **Note:** LarkSync is an independent open-source project and is not affiliated with, endorsed by, or sponsored by ByteDance (Lark/Feishu) or Google LLC.

*© 2026 Khiem Nguyen Dinh · Kstudy Academy*
