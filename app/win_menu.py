"""
Windows system tray menu extensions.
The About dialog is shared with macOS — see app/about_dialog.py.
"""

from app.about_dialog import show_about


def _show_about():
    show_about()
