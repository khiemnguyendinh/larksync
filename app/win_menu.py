"""
Windows System Tray Menu extensions.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

CREDIT_TEXT = (
    "LarkSync\n\n"
    "Sync Lark Drive -> Google Drive automatically.\n\n"
    "Developed by:\n"
    "Khiem Nguyen Dinh\n"
    "Kstudy Academy\n"
    "www.kstudy.edu.vn\n"
    "khiem@kstudy.edu.vn\n\n"
    "© 2026 Kstudy Academy. All rights reserved."
)

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
