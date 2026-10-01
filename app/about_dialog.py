"""About dialog shared by the macOS menu bar and the Windows tray menu."""

from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from app.version import __version__, WEBSITE

CREDIT_TEXT = (
    f"LarkSync {__version__}\n\n"
    "Sync Lark Drive → Google Drive automatically.\n\n"
    "Developed by:\n"
    "Khiem Nguyen Dinh\n"
    "Kstudy Academy\n"
    "www.kstudy.edu.vn\n"
    "khiem@kstudy.edu.vn\n\n"
    "© 2026 Kstudy Academy. All rights reserved."
)


def show_about(parent=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("About LarkSync")
    dlg.setFixedSize(340, 300)
    dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(24, 20, 24, 16)
    layout.setSpacing(12)

    lbl = QLabel(CREDIT_TEXT)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("font-size: 12px;")
    layout.addWidget(lbl)

    link = QLabel(f'<a href="{WEBSITE}">www.kstudy.edu.vn</a>')
    link.setAlignment(Qt.AlignmentFlag.AlignCenter)
    link.setOpenExternalLinks(True)
    link.setStyleSheet("font-size: 11px;")
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
