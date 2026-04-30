"""Log Viewer Dialog — scrollable, color-coded, exportable."""

from pathlib import Path
from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QFont, QTextCharFormat, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QFileDialog, QWidget
)

FOOTER_TEXT = "Sponsored by Kstudy Academy · www.kstudy.edu.vn"


def _dark() -> bool:
    from PyQt6.QtWidgets import QApplication
    return QApplication.palette().window().color().lightness() < 128

def _c(light: str, dark: str) -> str:
    return dark if _dark() else light


class LogViewer(QDialog):
    def __init__(self, log_path: str, parent=None):
        super().__init__(parent)
        self.log_path = log_path
        self.setWindowTitle("Sync Log")
        self.setFixedSize(600, 420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Log text area — always dark (terminal aesthetic)
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("SF Mono, Menlo, monospace", 11))
        self._text.setStyleSheet(
            "background:#1e1e1e; color:#ccc; border:none;"
            "padding:10px; selection-background-color:#264F78;"
        )
        root.addWidget(self._text, 1)

        # Button bar
        bar_bg  = _c("#ffffff", "#1c1c1e")
        bar_sep = _c("#f0f0f0", "#3a3a3c")
        btn_bdr = _c("#d0d0d0", "#444444")
        btn_fg  = _c("#333333", "#e0e0e0")
        btn_bg  = _c("#ffffff", "#2c2c2e")
        bar = QWidget()
        bar.setStyleSheet(f"background:{bar_bg}; border-top:1px solid {bar_sep};")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)

        _btn_style = (
            f"border:1px solid {btn_bdr}; border-radius:6px; padding:5px 12px;"
            f"font-size:11px; background:{btn_bg}; color:{btn_fg};"
        )
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._load)
        refresh.setStyleSheet(_btn_style)

        clear = QPushButton("Clear Log")
        clear.clicked.connect(self._clear)
        clear.setStyleSheet(_btn_style)

        export = QPushButton("Export…")
        export.clicked.connect(self._export)
        export.setStyleSheet(_btn_style)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        close.setStyleSheet(
            "background:#007AFF; color:white; border:none;"
            "border-radius:6px; padding:5px 14px; font-size:11px; font-weight:600;"
        )

        bar_layout.addWidget(refresh)
        bar_layout.addWidget(clear)
        bar_layout.addWidget(export)
        bar_layout.addStretch()
        bar_layout.addWidget(close)
        root.addWidget(bar)

        # Footer
        footer_fg  = _c("#888888", "#666666")
        footer_sep = _c("#f0f0f0", "#3a3a3c")
        footer = QLabel(FOOTER_TEXT)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFixedHeight(24)
        footer.setStyleSheet(
            f"color:{footer_fg}; font-size:10px;"
            f"border-top:1px solid {footer_sep}; padding-top:2px;"
        )
        root.addWidget(footer)

        self._load()

    def _load(self):
        self._text.clear()
        path = Path(self.log_path)
        if not path.exists():
            self._text.setPlainText("No log file found.")
            return

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        # Show last 500 lines
        for line in lines[-500:]:
            self._append_colored(line)
        # Scroll to bottom
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _append_colored(self, line: str):
        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        fmt = QTextCharFormat()

        if "[ERROR]" in line or "[CRITICAL]" in line:
            fmt.setForeground(QColor("#F44747"))
        elif "[WARNING]" in line or "[WARN]" in line:
            fmt.setForeground(QColor("#FFD700"))
        elif "[INFO]" in line:
            fmt.setForeground(QColor("#4EC9B0"))
        else:
            fmt.setForeground(QColor("#888"))

        cursor.insertText(line + "\n", fmt)

    def _clear(self):
        path = Path(self.log_path)
        if path.exists():
            path.write_text("")
        self._text.clear()

    def _export(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "sync.log", "Log Files (*.log);;Text Files (*.txt)"
        )
        if dest:
            import shutil
            shutil.copy(self.log_path, dest)
