#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# LarkSync — Build Script
# Produces: dist/LarkSync.app  +  dist/LarkSync.dmg
#
# Requirements: Python 3.11+, pip3
# Run: bash build.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_NAME="LarkSync"
VERSION="1.0.0"
DIST_DIR="dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
DMG_PATH="${DIST_DIR}/${APP_NAME}.dmg"

echo "═══════════════════════════════════════"
echo "  Building ${APP_NAME} v${VERSION}"
echo "═══════════════════════════════════════"

# ── 1. Install dependencies ───────────────────────────────────────────
echo ""
echo "▸ Installing dependencies..."
pip3 install --quiet \
    PyQt6 \
    requests \
    google-api-python-client \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    py2app \
    dmgbuild

# ── 2. Prepare app icon from user-supplied PNG ────────────────────────
echo "▸ Preparing icon from user PNG..."
mkdir -p assets
ICON_SRC="${HOME}/Desktop/larksync icon.png"
if [ ! -f "${ICON_SRC}" ]; then
    echo "  ✕ Source icon not found at: ${ICON_SRC}"
    exit 1
fi

# Copy source as-is (master 1024 — sips will resize from it)
cp "${ICON_SRC}" assets/icon_1024.png

# Generate .icns using sips + iconutil — resize the user's PNG only
rm -rf assets/icon.iconset
mkdir -p assets/icon.iconset
sizes=(16 32 64 128 256 512 1024)
for s in "${sizes[@]}"; do
    sips -z "$s" "$s" assets/icon_1024.png \
        --out "assets/icon.iconset/icon_${s}x${s}.png" >/dev/null 2>&1
    if [ "$s" -le 512 ]; then
        s2=$((s * 2))
        sips -z "$s2" "$s2" assets/icon_1024.png \
            --out "assets/icon.iconset/icon_${s}x${s}@2x.png" >/dev/null 2>&1
    fi
done
iconutil -c icns assets/icon.iconset -o assets/icon.icns 2>/dev/null \
    || echo "  ⚠ iconutil failed — icon skipped"
echo "  ✓ Icon prepared from ${ICON_SRC}"

# ── 3. Copy sync modules ──────────────────────────────────────────────
echo "▸ Preparing sync modules..."
mkdir -p sync app

# Copy existing sync scripts if available in parent directory
SYNC_SRC="../lark_gdrive_sync"
if [ -d "$SYNC_SRC" ]; then
    for f in lark_client.py lark_auth.py google_client.py sync_engine.py lark_notifier.py; do
        if [ -f "${SYNC_SRC}/${f}" ] && [ ! -f "sync/${f}" ]; then
            cp "${SYNC_SRC}/${f}" "sync/${f}"
        fi
    done
    echo "  Synced modules from ${SYNC_SRC}"
else
    echo "  ⚠ sync/ modules must be present — copy manually if missing"
fi

# Create __init__.py files
touch sync/__init__.py app/__init__.py

# ── 4. Clean previous build ───────────────────────────────────────────
echo "▸ Cleaning previous build..."
rm -rf build "${DIST_DIR}"

# ── 5. Build .app ─────────────────────────────────────────────────────
echo "▸ Building .app bundle (this may take 2-3 minutes)..."
python3 setup.py py2app --quiet

echo "  ✓ App built: ${APP_PATH}"

# ── 5b. Override py2app default icon with user PNG ────────────────────
BUNDLE_ICON="${APP_PATH}/Contents/Resources/PythonApplet.icns"
if [ -f assets/icon.icns ] && [ -d "${APP_PATH}/Contents/Resources" ]; then
    cp assets/icon.icns "${BUNDLE_ICON}"
    # Refresh Finder/LaunchServices icon cache for this bundle
    touch "${APP_PATH}"
    echo "  ✓ Bundle icon replaced with user PNG"
fi

# ── 6. Post-build size optimisation ──────────────────────────────────
echo "▸ Trimming bundle (removing unused files)..."
# Detect Python version inside bundle
PYVER=$(ls "${APP_PATH}/Contents/Resources/lib/" | grep -E '^python3\.' | head -1)
PYLIB="${APP_PATH}/Contents/Resources/lib/${PYVER}"
QT6="${PYLIB}/PyQt6/Qt6"
echo "  Detected: ${PYVER}"

# googleapiclient discovery cache — the single biggest win (~95 MB)
rm -rf "${PYLIB}/googleapiclient/discovery_cache"

# QML runtime — not used by a Widgets app (~26 MB)
rm -rf "${QT6}/qml"

# FFmpeg / multimedia dylibs — not needed (~18 MB)
rm -f  "${QT6}/lib/libavcodec"*.dylib
rm -f  "${QT6}/lib/libavformat"*.dylib
rm -f  "${QT6}/lib/libavutil"*.dylib
rm -f  "${QT6}/lib/libswscale"*.dylib
rm -f  "${QT6}/lib/libswresample"*.dylib

# Qt translations — keep only English (~9 MB saved)
find "${QT6}/translations" -type f ! -name "*en*" -delete 2>/dev/null

# setuptools not needed at runtime (~9 MB)
rm -rf "${PYLIB}/setuptools"

# Tcl/Tk framework (tkinter) not used (~12 MB)
rm -rf "${APP_PATH}/Contents/Frameworks/Tcl.framework"
rm -rf "${APP_PATH}/Contents/Frameworks/Tk.framework"

BEFORE=407
AFTER=$(du -sm "${APP_PATH}" 2>/dev/null | awk '{print $1}')
echo "  ✓ Bundle trimmed: ~${BEFORE} MB → ${AFTER} MB"

# ── 7. Build .dmg ─────────────────────────────────────────────────────
echo "▸ Building .dmg installer..."

# Write dmg settings inline
cat > /tmp/dmg_settings.py << DMGPY
import os
application = '${APP_PATH}'
appname     = '${APP_NAME}'
size        = None
files       = [application]
symlinks    = {'Applications': '/Applications'}
icon_locations = {
    appname + '.app': (150, 180),
    'Applications':   (350, 180),
}
background    = 'builtin-arrow'
show_status_bar = False
show_tab_view   = False
show_toolbar    = False
show_pathbar    = False
show_sidebar    = False
sidebar_width   = 180
window_rect     = ((200, 120), (520, 360))
default_view    = 'icon-view'
icon_size       = 80
DMGPY

python3 -m dmgbuild \
    -s /tmp/dmg_settings.py \
    "${APP_NAME}" \
    "${DMG_PATH}" \
    2>/dev/null || {
        # Fallback: simple hdiutil approach
        hdiutil create -volname "${APP_NAME}" \
            -srcfolder "${DIST_DIR}/${APP_NAME}.app" \
            -ov -format UDZO "${DMG_PATH}"
    }

echo "  ✓ Installer built: ${DMG_PATH}"

# ── 8. Summary ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════"
echo "  Build Complete!"
echo "  App:  ${APP_PATH}"
echo "  DMG:  ${DMG_PATH}"
echo ""
echo "  To install:"
echo "  Open ${DMG_PATH} → drag ${APP_NAME} to Applications"
echo ""
echo "  First launch: right-click → Open (bypass Gatekeeper)"
echo "═══════════════════════════════════════"
