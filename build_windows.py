"""
Windows build (PyInstaller, one-folder, windowed)

    python build_windows.py

Output : dist/LarkSync/LarkSync.exe          (+ dist/LarkSync-<version>-Windows.zip)
Single source of truth for the Windows build — build_windows.cmd and the GitHub
Actions workflow both call this script (they used to carry diverging copies of
the options, and the local one used ':' as the --add-data separator, which
PyInstaller rejects on Windows).
Also runs on macOS / Linux, which is how CI checks the options without Windows.
"""

import os
import re
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

NAME    = "LarkSync"
VERSION = re.search(r'__version__\s*=\s*"([^"]+)"',
                    (ROOT / "app" / "version.py").read_text(encoding="utf-8")).group(1)
SEP     = os.pathsep            # ';' on Windows, ':' elsewhere — what --add-data expects


def write_version_info() -> str:
    """Explorer > Properties > Details metadata (publisher, version) for LarkSync.exe."""
    parts = [int(p) for p in VERSION.split(".")[:3]] + [0] * 3
    tup = tuple(parts[:4])
    dotted = ".".join(str(n) for n in tup)
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Kstudy Academy'),
      StringStruct('FileDescription', 'LarkSync - Lark Drive to Google Drive sync'),
      StringStruct('FileVersion', '{dotted}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('LegalCopyright', '\\xa9 2026 Khiem Nguyen Dinh - Kstudy Academy'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', '{NAME}'),
      StringStruct('ProductVersion', '{dotted}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    out = ROOT / "build" / "version_info.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return str(out)


def drive_discovery_doc() -> Path:
    """googleapiclient builds the Drive service from this bundled JSON file."""
    import googleapiclient
    doc = Path(googleapiclient.__file__).parent / "discovery_cache" / "documents" / "drive.v3.json"
    if not doc.exists():
        sys.exit(f"drive.v3.json not found at {doc} — reinstall google-api-python-client")
    return doc


def main():
    args = [
        "main.py",
        f"--name={NAME}",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--add-data=assets{SEP}assets",
        # Only the one discovery document we need (all of them are ~95 MB).
        f"--add-data={drive_discovery_doc()}{SEP}googleapiclient/discovery_cache/documents",
        "--collect-submodules=app",
        "--collect-submodules=sync",
        "--hidden-import=google_auth_httplib2",
        "--exclude-module=tkinter",
    ]
    icon = ROOT / "assets" / "icon.ico"
    if icon.exists():
        args.append(f"--icon={icon}")
    if sys.platform == "win32":
        args.append(f"--version-file={write_version_info()}")

    PyInstaller.__main__.run(args)

    out = ROOT / "dist" / NAME
    if not out.exists():
        sys.exit("PyInstaller did not produce dist/LarkSync")

    # Drop every other Google API discovery document that a hook may have collected.
    for doc in out.rglob("discovery_cache/documents/*.json"):
        if doc.name != "drive.v3.json":
            doc.unlink()

    size_mb = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"\nBuilt {out}  ({size_mb:.0f} MB, v{VERSION})")

    archive = shutil.make_archive(str(ROOT / "dist" / f"{NAME}-{VERSION}-Windows"), "zip", out.parent, NAME)
    print(f"Zip   {archive}")


if __name__ == "__main__":
    main()
