# Changelog

All notable changes to LarkSync. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow [SemVer](https://semver.org/).

## [1.1.0] — 2026-10-01

Release focus: make the **macOS** build correct first, then bring **Windows** to the same level, and put a test suite and CI behind both.

### Upgrading from 1.0.x

- **Your data moves.** v1.0.x kept settings and tokens in `~/Documents/lark_gdrive_sync`. v1.1 uses `~/Library/Application Support/LarkSync` (macOS) / `%APPDATA%\LarkSync` (Windows) and copies your existing files over on first launch (settings, Lark token, Google token, `credentials.json`, sync history, log). The old folder is **not** deleted. It contains your App Secret and tokens, so delete it once you have confirmed v1.1 works — especially if Documents is synced by iCloud / OneDrive.
- The Google token is converted from `google_token.pkl` to `google_token.json` automatically.
- If you run the Lark sign-in, make sure the Lark app's **Redirect URL** is exactly `http://localhost:8080/callback` (unchanged from 1.0.x, now documented in the User Guide).

### Fixed — Windows

- **Right-clicking the tray icon did nothing**, although every guide said to right-click. The menu is now attached to the tray icon; left-click opens Settings.
- **Tray icon was invisible on a dark taskbar** (black strokes on transparent). It is now blue (idle) / orange (syncing).
- **A second launch could terminate the running app.** The lock check used `os.kill(pid, 0)`, which on Windows calls `TerminateProcess`. It now uses a `QLockFile`, which also handles crashed instances.
- **`build_windows.py` could not build** (`--add-data` used `:` as separator; `assets/icon.ico` did not exist) and CI carried a diverging copy of the options. One script is now used everywhere, an icon is committed, and the exe carries version/publisher metadata.
- "Launch at login" pointed the registry at `python.exe` when run from source; it now launches the real exe (or `pythonw.exe main.py`).
- Clicking elsewhere could re-open Settings behind the tray menu (macOS Dock handler was active on Windows).
- `credentials.json` with non-ASCII content was rejected (default code page); files are now read as UTF-8.
- Log viewer monospace font fell back to a proportional font.
- Loopback OAuth server no longer sets `SO_REUSEADDR` on Windows, so a busy port is reported instead of silently shared.

### Fixed — macOS

- **Packaged app could not create the Google Drive service**: `build.sh` deleted the whole `googleapiclient/discovery_cache` package, which `build()` imports at runtime. Now only the large `documents/` folder is pruned (keeping `drive.v3.json`), and the bundle is self-tested after trimming.
- **"Launch at Login" never worked**: Settings compared the new value to the value it had just saved, and the LaunchAgent ran the bundled Python interpreter instead of the app. It now writes a LaunchAgent that runs `open -a LarkSync.app`.
- `build.sh` failed for anyone without `~/Desktop/larksync icon.png` and under `set -e` on missing folders; it used the global Python and fake size numbers. It now uses the committed icon, a private venv, real sizes, ad-hoc (or Developer-ID) signing, and `hdiutil` fallback with visible errors.
- The Dock-click handler could open Settings at launch and on top of other dialogs; it now ignores launch activation, goes through the single-dialog guard and never stacks.
- Secrets no longer live in `~/Documents` (iCloud sync, privacy prompt) — see above.

### Fixed — all platforms

- **Incremental sync could skip files forever**: the "last sync" marker advanced after crashes, cancels and runs with errors. A separate marker (`last_sync_clean`) now moves only after a run with zero errors.
- **Scheduler**: a missed slot (asleep / powered off) waited a whole extra week; a fresh install never scheduled anything until the first manual sync; "Next sync" showed next week when today's slot was still ahead; a bad value in the config raised inside the timer. Rewritten as pure functions with catch-up, re-arming on schedule change and retry back-off.
- **Cancel Sync** let the UI start a second sync over the first (and could destroy a running thread); it now stays busy until the worker really stops. Quitting during a sync no longer risks a crash.
- **Crashes produced two notifications** (error, then "0 files synced"); there is now exactly one completion event.
- **Browser sign-ins froze the window** (Google everywhere, Lark in Settings), and the wizard's Lark status never updated (UI callback posted from a thread with no event loop). Sign-ins now run on worker threads.
- Lark OAuth: the callback port stayed bound after a timeout (every retry failed), `state` was not verified, errors were not HTML-escaped, favicon requests could consume the single handled request.
- **Settings could only be saved by pressing "Sync Now"**; there is now a **Save** button. The status line reports cancelled / failed / with-errors instead of always "Sync complete".
- **"Skip existing files"** was offered but ignored by the engine.
- **Google**: a blank destination matched a same-named folder anywhere in the Drive; overwriting a file deleted/trashed in Drive failed forever (now recreated); expired refresh tokens (7-day "Testing" apps) crashed the sync (now a clear "Re-authorize Google" message, and background syncs never open a browser); Shared Drives are supported.
- **Lark**: no retry on 429/5xx; the file-size limit never applied (the file list has no size) — now enforced from `Content-Length`; shortcuts no longer count as errors; Cancel works during the initial folder listing.
- State file saved periodically and on cancel/crash (previously lost on crash → duplicate uploads); corrupt state/config are backed up instead of crashing.
- Logs rotate (2 MB × 3); windowed builds without `stderr` no longer fail in the logging handler.

### Added

- **Windows installer** (`LarkSync-Setup-<version>.exe`, Inno Setup, per-user, optional start-at-login and desktop shortcut), the **portable single-file** `LarkSync-<version>-Portable.exe` (carried over from the unmerged `windows` branch / PR #3, now built by the same script) and the folder `.zip`.
- **Unified CI** (`.github/workflows/build.yml`): tests on Linux/macOS/Windows, macOS `.dmg`, Windows installer + zip, draft GitHub release on `v*` tags.
- **`--selftest`** flag: checks a packaged build's imports, TLS bundle, icon, Drive discovery document and widgets; run by `build.sh` and CI.
- macOS: `⌘R` Sync Now and `⌘L` View Log in the File menu; optional Developer-ID signing + notarization in `build.sh`.
- Test suite (~120 tests) and `requirements-dev.txt`; version in one place (`app/version.py`), shown in the tray menu and About dialog.
- Documentation: User Guide wizard section rewritten to match the real wizard, Redirect URL step added, Windows guide, Architecture and Developer Guide updated, release checklist.

### Changed

- Config, tokens and sync state are written atomically with owner-only permissions (POSIX).
- Requirements split into `requirements.txt` (runtime), `requirements_macos.txt`, `requirements_windows.txt`, `requirements-dev.txt`.
- The `macos` / `windows` branch workflow is retired; `main` is built and tested for both platforms. Open PRs #2 (`macos`) and #3 (`windows`) are superseded by this release: their code changes are included (tray toggle fix is already in `main`; the portable single-file build is integrated), their README/guide edits are older than the rewritten docs.

### Known limitations

- Builds are not code-signed unless you supply a certificate (macOS: Developer ID + notarization; Windows: signtool). Users see the Gatekeeper / SmartScreen prompts described in the guides.
- The CI macOS build is Apple Silicon (arm64). Intel Macs must build from source.
- Not verified against live Lark/Google accounts in this release: the Lark API behaviours assumed by the new code (the `state` echo on the OAuth redirect, `Content-Length` on downloads) follow the documented API.
- Lark MindNote and Slides export rely on the export-task API supporting those types; failures are reported per file in the log.

## [1.0.0]

Initial release: Lark Drive → Google Drive sync, tray/menu-bar app, schedules, incremental sync, Lark notifications, Windows build.
