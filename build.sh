#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# LarkSync — macOS build
# Produces: dist/LarkSync.app  +  dist/LarkSync.dmg
#
# Requirements: macOS 12+, Python 3.11+ (python.org or Homebrew)
# Run:          bash build.sh
#
# Optional environment variables
#   ICON_SRC=/path/icon-1024.png  regenerate assets/icon.icns from a 1024px PNG
#                                 (default: use the committed assets/icon.icns)
#   CODESIGN_IDENTITY="Developer ID Application: Name (TEAMID)"
#                                 sign with your Apple Developer ID (hardened runtime)
#                                 default: ad-hoc signature (needed to launch on Apple Silicon)
#   NOTARY_PROFILE=profile        `xcrun notarytool store-credentials` profile; with a
#                                 CODESIGN_IDENTITY the dmg is notarized + stapled
#   SKIP_VENV=1                   use the current Python environment (CI)
#   SKIP_SELFTEST=1               do not run the packaged-app self test
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="LarkSync"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' app/version.py)"
DIST_DIR="dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
DMG_PATH="${DIST_DIR}/${APP_NAME}.dmg"

if [ -z "${VERSION}" ]; then
    echo "Could not read the version from app/version.py" >&2
    exit 1
fi

echo "═══════════════════════════════════════"
echo "  Building ${APP_NAME} v${VERSION}"
echo "═══════════════════════════════════════"

# ── 1. Python environment ─────────────────────────────────────────────
echo ""
echo "▸ Preparing Python environment..."
if [ "${SKIP_VENV:-0}" != "1" ]; then
    # An isolated venv keeps the build reproducible and the system Python clean.
    python3 -m venv .build-venv
    # shellcheck disable=SC1091
    source .build-venv/bin/activate
fi
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r requirements_macos.txt
echo "  ✓ $(python3 --version)"

# ── 2. App icon ───────────────────────────────────────────────────────
if [ -n "${ICON_SRC:-}" ]; then
    echo "▸ Regenerating icon from ${ICON_SRC}..."
    [ -f "${ICON_SRC}" ] || { echo "  ✕ ICON_SRC not found" >&2; exit 1; }
    rm -rf assets/icon.iconset
    mkdir -p assets/icon.iconset
    for s in 16 32 64 128 256 512; do
        sips -z "$s" "$s" "${ICON_SRC}" --out "assets/icon.iconset/icon_${s}x${s}.png" >/dev/null
        s2=$((s * 2))
        sips -z "$s2" "$s2" "${ICON_SRC}" --out "assets/icon.iconset/icon_${s}x${s}@2x.png" >/dev/null
    done
    iconutil -c icns assets/icon.iconset -o assets/icon.icns
    rm -rf assets/icon.iconset
    echo "  ✓ assets/icon.icns updated"
fi
[ -f assets/icon.icns ] || { echo "✕ assets/icon.icns is missing (set ICON_SRC to generate it)" >&2; exit 1; }

# ── 3. Clean previous build ───────────────────────────────────────────
echo "▸ Cleaning previous build..."
rm -rf build "${DIST_DIR}"

# ── 4. Build .app ─────────────────────────────────────────────────────
echo "▸ Building .app bundle (this may take 2-3 minutes)..."
python3 setup.py py2app --quiet
[ -d "${APP_PATH}" ] || { echo "✕ py2app did not produce ${APP_PATH}" >&2; exit 1; }
SIZE_BEFORE=$(du -sm "${APP_PATH}" | awk '{print $1}')
echo "  ✓ App built: ${APP_PATH} (${SIZE_BEFORE} MB)"

ICON_NAME=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIconFile" "${APP_PATH}/Contents/Info.plist" 2>/dev/null || true)
echo "  ✓ Bundle icon: ${ICON_NAME:-<none>}"

# ── 5. Post-build size optimisation ──────────────────────────────────
echo "▸ Trimming bundle (removing unused files)..."
PYLIB=$(find "${APP_PATH}/Contents/Resources/lib" -maxdepth 1 -type d -name 'python3.*' | head -1)
if [ -z "${PYLIB}" ]; then
    echo "  ⚠ Python library folder not found — skipping trim"
else
    QT6="${PYLIB}/PyQt6/Qt6"
    echo "  Detected: $(basename "${PYLIB}")"

    # googleapiclient ships ~95 MB of discovery documents for every Google API.
    # Keep ONLY drive.v3.json: build("drive","v3") reads it from disk.
    # NOTE: the discovery_cache *package* must stay — googleapiclient imports it at
    # runtime (v1.0.x deleted the whole folder, which breaks the Google service).
    DOCS="${PYLIB}/googleapiclient/discovery_cache/documents"
    if [ -d "${DOCS}" ]; then
        find "${DOCS}" -type f ! -name 'drive.v3.json' -delete
    fi

    # QML runtime — not used by a Widgets app
    rm -rf "${QT6}/qml" || true
    # FFmpeg / multimedia dylibs — not needed
    rm -f "${QT6}/lib/libavcodec"*.dylib "${QT6}/lib/libavformat"*.dylib \
          "${QT6}/lib/libavutil"*.dylib "${QT6}/lib/libswscale"*.dylib \
          "${QT6}/lib/libswresample"*.dylib || true
    # Qt translations — keep only English
    find "${QT6}/translations" -type f ! -name "*en*" -delete 2>/dev/null || true
    # setuptools is not needed at runtime
    rm -rf "${PYLIB}/setuptools" || true
fi
# Tcl/Tk framework (tkinter) is not used
rm -rf "${APP_PATH}/Contents/Frameworks/Tcl.framework" "${APP_PATH}/Contents/Frameworks/Tk.framework" || true

# Trimming can leave symlinks that point at deleted files; codesign --strict rejects the
# whole bundle for them ("No such file or directory") and Gatekeeper would then call the
# app "damaged". Remove them (and say which, so a surprising one is visible).
DANGLING=$(find "${APP_PATH}" -type l ! -exec test -e {} \; -print)
if [ -n "${DANGLING}" ]; then
    echo "  Removing $(echo "${DANGLING}" | wc -l | tr -d ' ') dangling symlink(s):"
    echo "${DANGLING}" | head -20 | sed 's/^/    /'
    echo "${DANGLING}" | while IFS= read -r link; do rm -f "${link}"; done
fi

SIZE_AFTER=$(du -sm "${APP_PATH}" | awk '{print $1}')
echo "  ✓ Bundle trimmed: ${SIZE_BEFORE} MB → ${SIZE_AFTER} MB"

# ── 6. Self test of the packaged app ──────────────────────────────────
# Runs the real bundle in a throw-away data folder and checks that imports, the
# TLS bundle, icon and Google discovery document survived packaging + trimming.
if [ "${SKIP_SELFTEST:-0}" != "1" ]; then
    echo "▸ Self-testing the packaged app..."
    TEST_HOME="$(mktemp -d)"
    if LARKSYNC_HOME="${TEST_HOME}" LARKSYNC_SELFTEST_OUT="${TEST_HOME}/selftest.txt" \
           "${APP_PATH}/Contents/MacOS/${APP_NAME}" --selftest; then
        echo "  ✓ Self test passed"
    else
        echo "  ✕ Self test FAILED:" >&2
        cat "${TEST_HOME}/selftest.txt" >&2 || true
        exit 1
    fi
    rm -rf "${TEST_HOME}"
fi

# ── 7. Code signing ───────────────────────────────────────────────────
echo "▸ Signing..."
if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    codesign --force --deep --options runtime --timestamp \
        --entitlements installer/macos/entitlements.plist \
        --sign "${CODESIGN_IDENTITY}" "${APP_PATH}"
    echo "  ✓ Signed with: ${CODESIGN_IDENTITY}"
else
    # Apple Silicon refuses to run a bundle whose signature was invalidated by
    # trimming; an ad-hoc signature is enough for local use (not for distribution).
    codesign --force --deep --sign - "${APP_PATH}"
    echo "  ✓ Ad-hoc signed (set CODESIGN_IDENTITY for a distributable build)"
fi
# Fatal: an app whose seal is broken is reported as "damaged" by Gatekeeper.
if codesign --verify --deep --strict --verbose=2 "${APP_PATH}"; then
    echo "  ✓ Signature verified"
else
    echo "  ✕ codesign verification failed" >&2
    exit 1
fi

# ── 8. Build .dmg ─────────────────────────────────────────────────────
echo "▸ Building .dmg installer..."
DMG_SETTINGS="$(mktemp -t larksync_dmg).py"
cat > "${DMG_SETTINGS}" << DMGPY
application = '${APP_PATH}'
appname     = '${APP_NAME}'
size        = None
files       = [application]
symlinks    = {'Applications': '/Applications'}
icon_locations = {
    appname + '.app': (150, 180),
    'Applications':   (350, 180),
}
background      = 'builtin-arrow'
show_status_bar = False
show_tab_view   = False
show_toolbar    = False
show_pathbar    = False
show_sidebar    = False
window_rect     = ((200, 120), (520, 360))
default_view    = 'icon-view'
icon_size       = 80
DMGPY

if python3 -m dmgbuild -s "${DMG_SETTINGS}" "${APP_NAME}" "${DMG_PATH}"; then
    echo "  ✓ dmgbuild OK"
else
    echo "  ⚠ dmgbuild failed — falling back to a plain hdiutil image"
    hdiutil create -volname "${APP_NAME}" -srcfolder "${APP_PATH}" -ov -format UDZO "${DMG_PATH}"
fi
rm -f "${DMG_SETTINGS}"

if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    codesign --force --timestamp --sign "${CODESIGN_IDENTITY}" "${DMG_PATH}"
    if [ -n "${NOTARY_PROFILE:-}" ]; then
        echo "▸ Notarizing (this can take a few minutes)..."
        xcrun notarytool submit "${DMG_PATH}" --keychain-profile "${NOTARY_PROFILE}" --wait
        xcrun stapler staple "${DMG_PATH}"
        echo "  ✓ Notarized and stapled"
    else
        echo "  ⚠ NOTARY_PROFILE not set — the dmg is signed but not notarized"
    fi
fi
echo "  ✓ Installer built: ${DMG_PATH} ($(du -sm "${DMG_PATH}" | awk '{print $1}') MB)"

# ── 9. Summary ────────────────────────────────────────────────────────
ARCHS=$(lipo -archs "${APP_PATH}/Contents/MacOS/${APP_NAME}" 2>/dev/null || echo "unknown")
echo ""
echo "═══════════════════════════════════════"
echo "  Build Complete!  (v${VERSION}, ${ARCHS})"
echo "  App:  ${APP_PATH}"
echo "  DMG:  ${DMG_PATH}"
echo ""
echo "  To install:"
echo "  Open ${DMG_PATH} → drag ${APP_NAME} to Applications"
if [ -z "${CODESIGN_IDENTITY:-}" ]; then
    echo ""
    echo "  Not notarized: on first launch right-click → Open"
    echo "  (or: xattr -cr /Applications/${APP_NAME}.app)"
fi
echo "═══════════════════════════════════════"
