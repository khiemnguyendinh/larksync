<div align="center">

# 🪟 LarkSync for Windows

**Complete guide for installing and using LarkSync on Windows.**

</div>

---

## Download & Install

### Option 1: Installer (Recommended)

1. Open the **[Releases page](https://github.com/khiemnguyendinh/larksync/releases)** and download **`LarkSync-Setup-<version>.exe`**.
   (No release yet? Open **[Actions → Build & Test](https://github.com/khiemnguyendinh/larksync/actions/workflows/build.yml)**, pick the latest green run and download the **LarkSync-Windows** artifact.)
2. Run it. It installs for your user only — **no administrator rights needed** — and offers a Start-menu entry, an optional desktop shortcut and an optional "start LarkSync when I sign in" checkbox.
3. Launch **LarkSync** from the Start menu. Uninstall any time from **Settings → Apps**.

### Option 2: Portable ZIP

Download **`LarkSync-<version>-Windows.zip`** (same places as above), extract it anywhere and double-click **`LarkSync.exe`**.

> **Windows SmartScreen:** If you see "Windows protected your PC", click **More info** → **Run anyway**. This happens because the app is not code-signed — it is safe to run.

### Option 3: Build from Source

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

# Build the .exe (+ .zip)
build_windows.cmd            # or: python build_windows.py
# Output: dist\LarkSync\LarkSync.exe

# Optional: the Setup.exe installer (needs Inno Setup 6.3+, https://jrsoftware.org/isinfo.php)
iscc /DMyAppVersion=1.1.0 installer\windows\LarkSync.iss
# Output: dist\LarkSync-Setup-1.1.0.exe
```

Check a build with `dist\LarkSync\LarkSync.exe --selftest` (writes the result to `%APPDATA%\LarkSync\selftest.txt`).

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

LarkSync runs in the **system tray** (notification area) at the bottom-right corner of your screen. Look for the blue ⟳ icon (it turns orange while a sync is running).

**Left-click** the icon to open **Settings**. **Right-click** it to access:

| Menu Item | Action |
|-----------|--------|
| **Sync Now** | Start a manual sync immediately |
| **Cancel Sync** | Stop a running sync (shows "Cancelling…" until it has really stopped) |
| **Last sync / Next sync** | View sync schedule info |
| **Settings…** | Open the Settings dialog |
| **View Log…** | Open the sync log viewer |
| **About LarkSync** | View credits and version info |
| **Quit LarkSync** | Exit the application |

### Settings

Access Settings from the tray menu → **Settings…**

| Tab | What you can configure |
|-----|----------------------|
| **General** | Launch at login, sync schedule, sync mode (incremental/full), conflict resolution (**Save** stores the changes; **Sync Now** saves and starts a sync) |
| **Larksuite** | Lark App ID, App Secret, re-authorize connection |
| **Google Drive** | credentials.json, Folder ID, re-authorize connection |
| **Notifications** | Lark group chat ID for sync notifications |

### Launch at Login

When enabled, LarkSync will automatically start when you log into Windows. This is done via the Windows Registry (`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`). The entry always points at the real `LarkSync.exe`, and uninstalling removes it.

### Scheduled syncs after the PC was off

If the PC was switched off or asleep at the scheduled time, LarkSync catches up within a minute of starting (see the [User Guide](docs/USER_GUIDE.md#schedule)). Turn on **Launch at Login** so it is running when you switch the PC on.

---

## Data Storage

All configuration and data files are stored in (paste into the Explorer address bar):

```
%APPDATA%\LarkSync\
├── app_config.json      # Your settings (includes the Lark App Secret)
├── credentials.json     # Google OAuth credentials
├── google_token.json    # Google auth token
├── lark_token.json      # Lark auth token
├── sync_state.json      # Sync progress state
├── sync.log             # Sync log (rotates at 2 MB, keeps 2 older files)
├── sync.lock            # Present only while a sync runs
└── instance.lock        # Present only while the app runs
```

**Upgrading from 1.0.x?** Your data lived in `%USERPROFILE%\Documents\lark_gdrive_sync\` (a folder OneDrive often syncs to the cloud). LarkSync copies it to the new location on first launch and leaves the old folder untouched — delete it once you have confirmed everything works, because it contains your App Secret and tokens.

---

## Troubleshooting

### "Windows protected your PC" (SmartScreen)
Click **More info** → **Run anyway**. The app is safe — this warning appears for unsigned applications.

### App doesn't appear in system tray
Click the **^** arrow on the taskbar (near the clock) to expand the hidden system tray icons. You can drag the LarkSync icon out to pin it.

### Right-clicking the tray icon shows nothing
Fixed in 1.1.0 (the menu is now attached to the tray icon). If you are on 1.0.x, update; the quick workaround there was to **left-click** the icon.

### The tray icon is invisible on a dark taskbar
Fixed in 1.1.0: the icon is blue/orange instead of black.

### Sync fails with "Lark authorization expired" / "No Lark authorization found"
Re-authorize Lark: Open **Settings** → **Larksuite** tab → Click **Re-authorize Lark**.

### Sync fails with "Google authorization expired"
Re-authorize Google: Open **Settings** → **Google Drive** tab → Click **Re-authorize Google**. (If your Google Cloud OAuth consent screen is in *Testing*, Google expires the sign-in every 7 days.)

### "Port 8080 is in use"
Another program is using the port Lark redirects to. Close it and click **Re-authorize Lark** again.

### "LarkSync is already running"
Only one copy can run. Look in the system tray (click **^**). If it crashed, just start it again — the stale lock is detected automatically; no file needs deleting.

---

## Differences from macOS Version

LarkSync for Windows is functionally **identical** to the macOS version. The only differences are platform-specific:

| Feature | macOS | Windows |
|---------|-------|---------|
| System integration | Menu bar (top of screen) | System tray (bottom-right) |
| Native menu bar | Yes (File/Help menus at top) | No (replaced by tray menu items) |
| Tray icon | Black "template" icon, recolored by macOS | Blue / orange icon (readable on light and dark taskbars) |
| Click behaviour | Click toggles the menu | Right-click = menu, left-click = Settings |
| Launch at login | macOS LaunchAgent (.plist, runs `open -a LarkSync.app`) | Windows Registry (`HKCU\...\Run`) |
| App format | `.app` bundle (py2app) | `.exe` folder (PyInstaller) |
| Installer | `.dmg` drag-to-Applications | `Setup.exe` (per-user) or ZIP |
| Data folder | `~/Library/Application Support/LarkSync` | `%APPDATA%\LarkSync` |
| About dialog | In Help menu bar | In tray right-click menu |

---

*© 2026 Khiem Nguyen Dinh · Kstudy Academy · [www.kstudy.edu.vn](https://www.kstudy.edu.vn)*
