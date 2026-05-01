"""
macOS Application Menu Bar
Creates the File / Help menu bar that appears at the top of the screen.
Also handles dock-icon activation to re-open Settings.
"""

from PyQt6.QtCore    import Qt, QUrl
from PyQt6.QtGui     import QAction, QDesktopServices, QKeySequence
from PyQt6.QtWidgets import QMenuBar, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

CREDIT_TEXT = (
    "LarkSync\n\n"
    "Sync Lark Drive → Google Drive automatically.\n\n"
    "Developed by:\n"
    "Khiem Nguyen Dinh\n"
    "Kstudy Academy\n"
    "www.kstudy.edu.vn\n"
    "khiem@kstudy.edu.vn\n\n"
    "© 2026 Kstudy Academy. All rights reserved."
)

HELP_LINKS = [
    (
        "Create a Lark App (App ID & Secret)",
        "https://open.larksuite.com/app",
    ),
    (
        "Create OAuth 2.0 Client ID (Google)",
        "https://console.cloud.google.com/apis/credentials",
    ),
    (
        "How to find a Lark group chat ID",
        "https://open.larksuite.com/document/client-docs/bot-5/add-a-bot-to-a-group-and-get-the-group-id",
    ),
]


def build_menu_bar(config, tray_app) -> QMenuBar:
    """
    Return a QMenuBar(None) — on macOS this becomes the global application
    menu bar visible at the top of the screen.
    """
    bar = QMenuBar(None)   # None parent → macOS global menu bar

    # ── File ──────────────────────────────────────────────────────────
    file_menu = bar.addMenu("File")

    settings_act = QAction("Settings…", bar)
    settings_act.setShortcut(QKeySequence("Ctrl+,"))
    settings_act.triggered.connect(lambda: _open_settings(config, tray_app))
    file_menu.addAction(settings_act)

    file_menu.addSeparator()

    quit_act = QAction("Quit LarkSync", bar)
    quit_act.setShortcut(QKeySequence("Ctrl+Q"))
    quit_act.triggered.connect(tray_app._quit)
    file_menu.addAction(quit_act)

    # ── Help ──────────────────────────────────────────────────────────
    help_menu = bar.addMenu("Help")

    for label, url in HELP_LINKS:
        act = QAction(label + "…", bar)
        act.triggered.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
        help_menu.addAction(act)

    help_menu.addSeparator()

    about_act = QAction("About LarkSync", bar)
    about_act.triggered.connect(lambda: _show_about())
    help_menu.addAction(about_act)

    return bar


def _open_settings(config, tray_app):
    # Delegate to tray_app so the singleton guard is enforced
    tray_app._open_settings()


def _show_about():
    dlg = QDialog()
    dlg.setWindowTitle("About LarkSync")
    dlg.setFixedSize(340, 280)
    dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(24, 20, 24, 16)
    layout.setSpacing(12)

    lbl = QLabel(CREDIT_TEXT)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("font-size: 12px; line-height: 1.5;")
    layout.addWidget(lbl)

    link = QLabel('<a href="https://www.kstudy.edu.vn">www.kstudy.edu.vn</a>')
    link.setAlignment(Qt.AlignmentFlag.AlignCenter)
    link.setOpenExternalLinks(True)
    link.setStyleSheet("font-size: 11px; color: #007AFF;")
    layout.addWidget(link)

    layout.addStretch()

    btn = QPushButton("OK")
    btn.setFixedWidth(80)
    btn.setStyleSheet(
        "background:#007AFF; color:white; border:none;"
        "border-radius:7px; padding:6px 16px; font-size:12px; font-weight:600;"
    )
    btn.clicked.connect(dlg.accept)
    row = QHBoxLayout()
    row.addStretch()
    row.addWidget(btn)
    layout.addLayout(row)

    dlg.exec()
