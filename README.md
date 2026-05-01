<div align="center">

# LarkSync

**Sync Lark Drive → Google Drive, automatically.**  
A lightweight desktop app for seamless file synchronization — available for **macOS** and **Windows**.

[![Platform - macOS](https://img.shields.io/badge/platform-macOS%2012%2B-lightgrey?logo=apple)](https://github.com/khiemnguyendinh/larksync/releases)
[![Platform - Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-blue?logo=windows)](https://github.com/khiemnguyendinh/larksync/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Release](https://img.shields.io/github/v/release/khiemnguyendinh/larksync?color=orange)](https://github.com/khiemnguyendinh/larksync/releases)
[![Build Windows](https://img.shields.io/github/actions/workflow/status/khiemnguyendinh/larksync/build-windows.yml?branch=windows&label=Windows%20Build&logo=github)](https://github.com/khiemnguyendinh/larksync/actions/workflows/build-windows.yml)
[![Author](https://img.shields.io/badge/author-Khiem%20Nguyen%20Dinh-purple)](https://www.kstudy.edu.vn)

</div>

---

## Screenshot

> *Screenshot placeholder — add a screenshot of the menu bar and settings window here.*

![LarkSync menu bar screenshot](assets/screenshot.png)

---

## Features

- **Cross-platform** — Available for both macOS and Windows
- **Automatic sync** — Schedule syncs daily, weekly, or run on demand
- **System tray integration** — Lives quietly in the macOS menu bar or Windows system tray
- **Lark Drive support** — Works with Lark (Feishu) custom app credentials
- **Google Drive upload** — Uploads to any target folder in your Google Drive via OAuth 2.0
- **Format conversion** — Lark-native files (Docs, Sheets, Mindnotes) exported to Google-compatible formats (Docx, Xlsx, PDF)
- **Incremental sync** — Only sync new and modified files since last run (faster)
- **Smart Settings UX** — Sync Now button saves + triggers sync; Cancel Sync mid-flight; singleton window guard
- **Secure credential fields** — All API keys and IDs hidden by default with a 👁 eye toggle
- **Setup Wizard** — Guided first-time configuration for both Lark and Google credentials
- **Sync log** — In-app log viewer for reviewing sync history and diagnosing errors
- **Lark group notification** — Get notified in your Lark group chat after each sync
- **Launch at login** — Auto-start via macOS Login Items or Windows Registry
- **Lightweight** — Built with Python + PyQt6, packaged as `.app` (macOS) or `.exe` (Windows)

---

## Requirements

### External Credentials (Required for all users)
- **Lark App** with Drive read permissions (App ID + App Secret) — [Create one here](https://open.larksuite.com/app)
- **Google Cloud project** with Drive API enabled (`credentials.json`) — [Set up here](https://console.cloud.google.com/apis/credentials)

### Pre-built App (Recommended)

| Platform | Requirements |
|----------|-------------|
| **macOS** | macOS 12 Monterey or later (Apple Silicon and Intel) |
| **Windows** | Windows 10 or later (64-bit) |

> No Python installation required for pre-built apps.

### Build from Source
- Python 3.11 or later
- pip / virtualenv

---

## 🍎 macOS — Quick Install

1. Download the latest `LarkSync.dmg` from [Releases](https://github.com/khiemnguyendinh/larksync/releases).
2. Open the DMG and drag **LarkSync.app** to your **Applications** folder.
3. **First launch:** Right-click the app → **Open** → **Open** (bypasses Gatekeeper for unsigned apps).
4. The Setup Wizard will guide you through the rest.

> If macOS says the app is damaged, run: `xattr -cr /Applications/LarkSync.app`

---

## 🪟 Windows — Quick Install

1. Go to **[GitHub Actions → Build LarkSync (Windows)](https://github.com/khiemnguyendinh/larksync/actions/workflows/build-windows.yml)**.
2. Click the latest successful build run (green ✅).
3. Scroll to the **Artifacts** section → Download **LarkSync-Windows.zip**.
4. Extract the ZIP → Run **`LarkSync.exe`**.
5. The Setup Wizard will guide you through the rest.

> **Note:** The app will appear in your system tray (near the clock on your taskbar). Right-click the tray icon to access all features.

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

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run in development mode
python main.py

# 5. Build the .app bundle + .dmg installer
bash build.sh
# Output: dist/LarkSync.app + dist/LarkSync.dmg
```

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

# 5. Build the .exe (using PyInstaller)
build_windows.cmd
# Output: dist\LarkSync\LarkSync.exe
```

> **Tip:** You don't need a Windows machine to build the Windows version! The GitHub Actions workflow automatically builds the `.exe` whenever code is pushed to the `windows` branch. See [`.github/workflows/build-windows.yml`](.github/workflows/build-windows.yml).

**Dependencies:**
- `PyQt6` — Cross-platform UI framework
- `google-api-python-client` — Google Drive API
- `google-auth-oauthlib` — Google OAuth flow
- `requests` — HTTP client for Lark API
- `py2app` — macOS app bundler (macOS build only)
- `pyinstaller` — Windows executable bundler (Windows build only)

---

## Project Structure

```
larksync/
├── main.py                  # App entry point (cross-platform)
├── app/                     # Core application modules
│   ├── config_manager.py    # Config persistence + launch-at-login
│   ├── tray_app.py          # System tray / menu bar logic
│   ├── settings_dialog.py   # Tabbed settings window
│   ├── setup_wizard.py      # 4-step Setup Wizard
│   ├── sync_thread.py       # Background sync QThread
│   ├── log_viewer.py        # Sync log viewer
│   ├── mac_menu_bar.py      # macOS-specific native menu bar
│   └── win_menu.py          # Windows-specific About dialog
├── sync/                    # Sync engine
│   ├── lark_auth.py         # Lark OAuth flow
│   ├── lark_client.py       # Lark Drive API client
│   ├── google_client.py     # Google Drive API client
│   ├── sync_engine.py       # Core sync logic
│   └── lark_notifier.py     # Lark group chat notifications
├── assets/                  # Icons and images
├── docs/                    # Documentation
├── .github/workflows/       # CI/CD
│   └── build-windows.yml    # Auto-build Windows .exe
├── setup.py                 # py2app configuration (macOS)
├── build.sh                 # macOS build script
├── build_windows.py         # PyInstaller config (Windows)
├── build_windows.cmd        # Windows build script
├── requirements.txt         # macOS dependencies
└── requirements_windows.txt # Windows dependencies
```

---

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Stable release — merged from platform branches |
| `macos` | Active macOS development |
| `windows` | Active Windows development + CI build |

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
- Test on both platforms if possible (macOS + Windows)
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
