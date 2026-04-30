<div align="center">

# LarkSync

**Sync Lark Drive → Google Drive, automatically.**  
A lightweight macOS menu bar app for seamless file synchronization.

[![Platform](https://img.shields.io/badge/platform-macOS%2012%2B-lightgrey?logo=apple)](https://github.com/khiemledev/larksync/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Release](https://img.shields.io/github/v/release/khiemledev/larksync?color=orange)](https://github.com/khiemledev/larksync/releases)
[![Author](https://img.shields.io/badge/author-Khiem%20Nguyen%20Dinh-purple)](https://www.kstudy.edu.vn)

</div>

---

## Screenshot

> *Screenshot placeholder — add a screenshot of the menu bar and settings window here.*

![LarkSync menu bar screenshot](assets/screenshot.png)

---

## Features

- **Automatic sync** — Schedule syncs daily, weekly, or run on demand
- **Menu bar integration** — Lives quietly in the macOS menu bar; no dock icon required
- **Lark Drive support** — Works with Lark (Feishu) custom app credentials
- **Google Drive upload** — Uploads to any target folder in your Google Drive via OAuth 2.0
- **Format conversion** — Lark-native files (Docs, Sheets, Mindnotes) exported to Google-compatible formats (Docx, Xlsx, PDF)
- **Setup Wizard** — Guided first-time configuration for both Lark and Google credentials
- **Sync log** — In-app log viewer for reviewing sync history and diagnosing errors
- **Launch at login** — Optional auto-start via macOS Login Items
- **Lightweight** — Built with Python + PyQt6, packaged as a standalone `.app` via py2app

---

## Requirements

### Pre-built App (Recommended)
- macOS 12 Monterey or later (Apple Silicon and Intel)
- No Python installation required

### Build from Source
- macOS 12 Monterey or later
- Python 3.11 or later (Python 3.13 recommended)
- pip / virtualenv

### External Credentials (Required for all users)
- **Lark App** with Drive read permissions (App ID + App Secret)
- **Google Cloud project** with Drive API enabled (`credentials.json`)

---

## Quick Install

1. Download the latest `LarkSync.dmg` from [Releases](https://github.com/khiemledev/larksync/releases).
2. Open the DMG and drag **LarkSync.app** to your **Applications** folder.
3. **First launch:** Right-click the app → **Open** → **Open** (bypasses Gatekeeper for unsigned apps).
4. The Setup Wizard will guide you through the rest.

> If macOS says the app is damaged, run: `xattr -cr /Applications/LarkSync.app`

---

## Quick Start

After installation, the Setup Wizard will ask for:

| Step | What You Need |
|------|---------------|
| Lark App credentials | App ID + App Secret from [open.larksuite.com/app](https://open.larksuite.com/app) |
| Google credentials | `credentials.json` from [console.cloud.google.com](https://console.cloud.google.com) |
| Lark Folder Token | From the Lark Drive folder URL |
| Google Drive Folder ID | From the Google Drive folder URL |
| Sync schedule | Manual, Daily, or Weekly |

See the full [User Guide](docs/USER_GUIDE.md) for step-by-step instructions.

---

## Build from Source

```bash
# 1. Clone the repository
git clone https://github.com/khiemledev/larksync.git
cd larksync

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run in development mode
python main.py

# 5. Build the .app bundle (macOS only)
bash build.sh
# Output: dist/LarkSync.app
```

The build script uses `py2app` to create a self-contained `.app` bundle. Refer to `setup.py` for bundle configuration.

**Dependencies** (see `requirements.txt`):
- `PyQt6` — UI framework
- `lark-oapi` or equivalent Lark SDK — Lark API client
- `google-api-python-client` — Google Drive API
- `google-auth-oauthlib` — Google OAuth flow
- `py2app` — macOS app bundler (build only)

---

## Project Structure

```
larksync/
├── main.py              # App entry point
├── app/                 # Core application modules
│   ├── tray.py          # Menu bar / system tray logic
│   ├── settings.py      # Settings window and config persistence
│   ├── wizard.py        # Setup Wizard
│   └── log_viewer.py    # Sync log window
├── sync/                # Sync engine
│   ├── lark_client.py   # Lark Drive API client
│   ├── google_client.py # Google Drive API client
│   └── engine.py        # Core sync logic and scheduler
├── assets/              # Icons and images
├── docs/                # Documentation
│   ├── USER_GUIDE.md
│   ├── TERMS_OF_USE.md
│   └── DISCLAIMER.md
├── setup.py             # py2app configuration
├── build.sh             # Build script
└── requirements.txt
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | Installation, setup, and usage instructions (EN + VI) |
| [Terms of Use](docs/TERMS_OF_USE.md) | Terms governing use of LarkSync (EN + VI) |
| [Disclaimer](docs/DISCLAIMER.md) | Liability disclaimer and warranty information (EN + VI) |

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
- Test on both Apple Silicon and Intel if possible
- Update documentation as needed
- Do not commit credentials or token files

For bugs, please open a [GitHub Issue](https://github.com/khiemledev/larksync/issues) with a description of the problem and the relevant section of your sync log.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Credits & Acknowledgments

**Developer:** [Khiem Nguyen Dinh](https://www.kstudy.edu.vn) ([@khiemledev](https://github.com/khiemledev))  
**Organization:** [Kstudy Academy](https://www.kstudy.edu.vn)  
**Contact:** [khiem@kstudy.edu.vn](mailto:khiem@kstudy.edu.vn)

Built with:
- [Python](https://www.python.org/) & [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [Lark Open API](https://open.larksuite.com/)
- [Google Drive API](https://developers.google.com/drive)
- [py2app](https://py2app.readthedocs.io/)

---

> **Note:** LarkSync is an independent open-source project and is not affiliated with, endorsed by, or sponsored by ByteDance (Lark/Feishu) or Google LLC.

*© 2026 Khiem Nguyen Dinh · Kstudy Academy*
