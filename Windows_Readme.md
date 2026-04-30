<div align="center">

# 🪟 LarkSync for Windows

**Complete guide for installing and using LarkSync on Windows.**

</div>

---

## Download & Install

### Option 1: Download Pre-built (Recommended)

1. Go to **[GitHub Actions → Build LarkSync (Windows)](https://github.com/khiemnguyendinh/larksync/actions/workflows/build-windows.yml)**.
2. Click the **latest successful build** (green ✅ checkmark).
3. Scroll to the **Artifacts** section at the bottom of the page.
4. Click **LarkSync-Windows** to download the ZIP file.
5. **Extract** the ZIP to any folder (e.g. `C:\Program Files\LarkSync\` or `Desktop`).
6. Double-click **`LarkSync.exe`** to run.

> **Windows SmartScreen:** If you see "Windows protected your PC", click **More info** → **Run anyway**. This happens because the app is not code-signed — it is safe to run.

### Option 2: Build from Source

```powershell
# Clone the repository
git clone https://github.com/khiemnguyendinh/larksync.git
cd larksync

# Create a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements_windows.txt

# Run in development mode
python main.py

# Build the .exe
build_windows.cmd
# Output: dist\LarkSync\LarkSync.exe
```

---

## First Launch — Setup Wizard

When you run LarkSync for the first time, a **Setup Wizard** will guide you through 4 steps:

### Step 1: Connect Lark Drive

1. Go to [open.larksuite.com/app](https://open.larksuite.com/app)
2. Create a new app → go to **Credentials & Basic Info**
3. Copy your **App ID** and **App Secret**
4. Enable permissions: `drive:drive:readonly`, `drive:file`, `drive:export`
5. Add Redirect URL: `http://localhost:8080/callback`
6. Go to **App Release** → Publish the app
7. Paste App ID and App Secret into LarkSync → Click **Authorize Lark**

### Step 2: Connect Google Drive

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Google Drive API**
3. Create **OAuth 2.0 Client ID** → type: **Desktop app**
4. Download JSON → rename to `credentials.json`
5. Add your email as a **Test User** under OAuth consent screen → Audience
6. In LarkSync, click **Browse** → select your `credentials.json`
7. Click **Authorize Google** → complete the flow in your browser

### Step 3: Preferences

- **Sync Schedule:** Weekly (recommended), Daily, or Manual
- **Conflict Resolution:** Overwrite or Skip existing files
- **Notification:** Optionally enter a Lark group chat ID for sync notifications

### Step 4: Done!

Click **Start LarkSync** — the app will minimize to your **system tray** (near the clock on your taskbar).

---

## Using LarkSync on Windows

### System Tray

LarkSync runs in the **system tray** (notification area) at the bottom-right corner of your screen. Look for the green ⟳ icon.

**Right-click** the tray icon to access:

| Menu Item | Action |
|-----------|--------|
| **Sync Now** | Start a manual sync immediately |
| **Cancel Sync** | Stop a running sync |
| **Last sync / Next sync** | View sync schedule info |
| **Settings…** | Open the Settings dialog |
| **View Log…** | Open the sync log viewer |
| **About LarkSync** | View credits and version info |
| **Quit LarkSync** | Exit the application |

### Settings

Access Settings from the tray menu → **Settings…**

| Tab | What you can configure |
|-----|----------------------|
| **General** | Launch at login, sync schedule, sync mode (incremental/full), conflict resolution |
| **Larksuite** | Lark App ID, App Secret, re-authorize connection |
| **Google Drive** | credentials.json, Folder ID, re-authorize connection |
| **Notifications** | Lark group chat ID for sync notifications |

### Launch at Login

When enabled, LarkSync will automatically start when you log into Windows. This is done via the Windows Registry (`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`).

---

## Data Storage

All configuration and data files are stored in:

```
%USERPROFILE%\Documents\lark_gdrive_sync\
├── app_config.json      # Your settings
├── credentials.json     # Google OAuth credentials
├── google_token.pkl     # Google auth token
├── lark_token.json      # Lark auth token
├── sync_state.json      # Sync progress state
└── sync.log             # Sync log file
```

---

## Troubleshooting

### "Windows protected your PC" (SmartScreen)
Click **More info** → **Run anyway**. The app is safe — this warning appears for unsigned applications.

### App doesn't appear in system tray
Click the **^** arrow on the taskbar (near the clock) to expand the hidden system tray icons. You can drag the LarkSync icon out to pin it.

### Sync fails with "No Lark user token found"
Re-authorize Lark: Open **Settings** → **Larksuite** tab → Click **Re-authorize Lark**.

### Sync fails with Google errors
Re-authorize Google: Open **Settings** → **Google Drive** tab → Click **Re-authorize Google**.

### Lock file prevents sync
If the app crashed during a sync, delete the lock file:
```powershell
del %USERPROFILE%\.larksync.lock
```

---

## Differences from macOS Version

LarkSync for Windows is functionally **identical** to the macOS version. The only differences are platform-specific:

| Feature | macOS | Windows |
|---------|-------|---------|
| System integration | Menu bar (top of screen) | System tray (bottom-right) |
| Native menu bar | Yes (File/Help menus at top) | No (replaced by tray menu items) |
| Launch at login | macOS LaunchAgent (.plist) | Windows Registry |
| App format | `.app` bundle (py2app) | `.exe` folder (PyInstaller) |
| Installer | `.dmg` drag-to-Applications | ZIP extract and run |
| About dialog | In Help menu bar | In tray right-click menu |

---

*© 2026 Khiem Nguyen Dinh · Kstudy Academy · [www.kstudy.edu.vn](https://www.kstudy.edu.vn)*
