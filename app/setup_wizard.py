"""
Setup Wizard
4-step first-run wizard: Lark → Google Drive → Preferences → Done
Collapsible help panels, inline validation, footer branding.
"""

import shutil
import webbrowser
from pathlib import Path

from PyQt6.QtCore    import Qt, QTimer, pyqtSlot
from PyQt6.QtGui     import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QFrame, QStackedWidget,
    QWidget, QScrollArea, QSizePolicy, QSpacerItem,
)

from app.config_manager import (
    ConfigManager, APP_DIR, GOOGLE_CREDS, LARK_TOKEN, GOOGLE_TOKEN
)

FOOTER_TEXT = "Sponsored by Kstudy Academy · www.kstudy.edu.vn"
LARK_DEV_URL   = "https://open.larksuite.com/app"
GOOGLE_DEV_URL = "https://console.cloud.google.com"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOURS = [f"{h:02d}:00 {'AM' if h < 12 else 'PM'}" for h in range(24)]


# ──────────────────────────────────────────────────────────────────────
# Theme helpers — auto-adapts to macOS dark / light mode
# ──────────────────────────────────────────────────────────────────────

def _dark() -> bool:
    from PyQt6.QtWidgets import QApplication
    return QApplication.palette().window().color().lightness() < 128


def _c(light: str, dark: str) -> str:
    return dark if _dark() else light


# ──────────────────────────────────────────────────────────────────────
# Reusable widget helpers
# ──────────────────────────────────────────────────────────────────────

def _label(text: str, bold=False, color=None, size=13) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    f = lbl.font()
    f.setPointSize(size)
    f.setBold(bold)
    lbl.setFont(f)
    # Map legacy gray codes to adaptive equivalents; keep semantic colors as-is
    _adaptive = {"#1a1a1a": _c("#1a1a1a", "#e5e5e5"),
                 "#888":    _c("#888888", "#aaaaaa"),
                 "#999":    _c("#999999", "#aaaaaa"),
                 "#555":    _c("#555555", "#aaaaaa"),
                 "#666":    _c("#666666", "#999999"),
                 None:      _c("#1a1a1a", "#e5e5e5")}
    lbl.setStyleSheet(f"color: {_adaptive.get(color, color)};")
    return lbl


def _input(placeholder="", password=False) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if password:
        e.setEchoMode(QLineEdit.EchoMode.Password)
    border = _c("#d0d0d0", "#444444")
    bg     = _c("#fafafa", "#2c2c2e")
    fg     = _c("#333333", "#e0e0e0")
    e.setStyleSheet(f"""
        QLineEdit {{
            border: 1px solid {border};
            border-radius: 7px;
            padding: 7px 10px;
            font-size: 12px;
            background: {bg};
            color: {fg};
        }}
        QLineEdit:focus {{ border-color: #007AFF; }}
    """)
    return e


def _btn(text: str, primary=False, small=False) -> QPushButton:
    b = QPushButton(text)
    pad = "5px 12px" if small else "7px 18px"
    if primary:
        b.setStyleSheet(f"""
            QPushButton {{
                background: #007AFF; color: white; border: none;
                border-radius: 7px; padding: {pad}; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #0066DD; }}
            QPushButton:disabled {{ background: #b0c8f0; }}
        """)
    else:
        btn_bg = _c("#ffffff", "#3a3a3c")
        b.setStyleSheet(f"""
            QPushButton {{
                background: {btn_bg}; color: #007AFF;
                border: 1px solid #007AFF;
                border-radius: 7px; padding: {pad}; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(0,122,255,0.12); }}
        """)
    return b


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {_c('#e0e0e0', '#3a3a3c')};")
    return line


def _help_panel(lines: list[str]) -> QWidget:
    """Collapsible help panel — hidden by default."""
    panel = QWidget()
    panel.setVisible(False)
    panel_bg  = _c("#EFF6FF", "rgba(0,122,255,0.10)")
    panel_bdr = _c("#BFDBFE", "rgba(0,122,255,0.30)")
    txt_color = _c("#1E40AF", "#82b4ff")
    panel.setStyleSheet(f"""
        background: {panel_bg}; border: 1px solid {panel_bdr};
        border-radius: 8px; padding: 2px;
    """)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(3)
    for i, line in enumerate(lines):
        row = QHBoxLayout()
        num = QLabel(str(i + 1))
        num.setFixedSize(16, 16)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(
            "background: #007AFF; color: white; border-radius: 8px;"
            "font-size: 9px; font-weight: 700;"
        )
        text = QLabel(line)
        text.setOpenExternalLinks(True)
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {txt_color}; font-size: 11px; background: transparent; border: none;")
        row.addWidget(num)
        row.addWidget(text, 1)
        layout.addLayout(row)
    return panel


def _help_btn(label: str, panel: QWidget) -> QPushButton:
    """Toggle button that shows/hides a help panel."""
    b = QPushButton(f"?  {label}")
    b.setCheckable(True)
    border = _c("#d0d0d0", "#444444")
    fg     = _c("#888888", "#aaaaaa")
    b.setStyleSheet(f"""
        QPushButton {{
            background: transparent; color: {fg};
            border: 1px solid {border}; border-radius: 5px;
            padding: 2px 8px; font-size: 10px;
        }}
        QPushButton:checked {{
            color: #007AFF; border-color: #007AFF; background: rgba(0,122,255,0.12);
        }}
        QPushButton:hover {{ border-color: #007AFF; color: #007AFF; }}
    """)
    def toggle(checked):
        panel.setVisible(checked)
        b.setText("✕  Hide guide" if checked else f"?  {label}")
    b.toggled.connect(toggle)
    return b


def _status_label() -> QLabel:
    lbl = QLabel("")
    lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {_c('#888888', '#aaaaaa')};")
    return lbl


def _step_indicator(current: int, total: int = 4) -> QWidget:
    """Dot + line progress indicator."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    for i in range(1, total + 1):
        dot = QLabel(str(i) if i > current else ("✓" if i < current else str(i)))
        dot.setFixedSize(24, 24)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if i < current:
            style = "background:#34C759; color:white;"
        elif i == current:
            style = "background:#007AFF; color:white;"
        else:
            style = "background:#e5e5ea; color:#999;"
        dot.setStyleSheet(f"{style} border-radius:12px; font-size:10px; font-weight:700;")
        row.addWidget(dot)
        if i < total:
            line = QFrame()
            line.setFixedHeight(2)
            line.setFrameShape(QFrame.Shape.HLine)
            color = "#34C759" if i < current else "#e5e5ea"
            line.setStyleSheet(f"background:{color}; border:none;")
            row.addWidget(line, 1)
    return w


# ──────────────────────────────────────────────────────────────────────
# Main Wizard Dialog
# ──────────────────────────────────────────────────────────────────────

class SetupWizard(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("LarkSync Setup")
        self.setFixedSize(500, 620)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        # ── Root layout ───────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._stack = QStackedWidget()
        scroll.setWidget(self._stack)

        # Build pages
        self._pages = [
            self._build_step1(),
            self._build_step2(),
            self._build_step3(),
            self._build_step4(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)

        root.addWidget(scroll, 1)
        root.addWidget(self._build_footer())

        self._go_to(0)

    # ── Navigation ────────────────────────────────────────────────────

    def _go_to(self, idx: int):
        self._stack.setCurrentIndex(idx)

    # ── Step 1: Lark ──────────────────────────────────────────────────

    def _build_step1(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(8)

        layout.addWidget(_step_indicator(1))

        # Title row + help button
        title_row = QHBoxLayout()
        title_row.addWidget(_label("Connect Lark Drive", bold=True, size=15))
        help_panel = _help_panel([
            'Go to <a href="https://open.larksuite.com/app">open.larksuite.com/app</a>',
            "Create an app → open <b>Credentials & Basic Info</b>",
            "Enable permissions: <b>drive:drive:readonly</b>, <b>drive:file</b>, <b>drive:export</b>",
            "Add Redirect URL: <b>http://localhost:8080/callback</b>",
            "Go to <b>App Release</b> → Publish the app",
        ])
        title_row.addStretch()
        title_row.addWidget(_help_btn("How to get credentials", help_panel))
        layout.addLayout(title_row)
        layout.addWidget(_label("Enter your Lark Developer app credentials.", color="#888", size=11))
        layout.addWidget(help_panel)

        # Fields
        layout.addWidget(_label("App ID", bold=True, size=11, color="#555"))
        self._lark_app_id = _input("e.g. cli_a978f97663b81ed1")
        self._lark_app_id.setText(self.config.get("lark_app_id", ""))
        layout.addWidget(self._lark_app_id)

        layout.addWidget(_label("App Secret", bold=True, size=11, color="#555"))
        self._lark_secret = _input("App Secret", password=True)
        self._lark_secret.setText(self.config.get("lark_app_secret", ""))
        layout.addWidget(self._lark_secret)

        # Auth button + status
        auth_row = QHBoxLayout()
        auth_btn = _btn("Authorize Lark →")
        auth_btn.clicked.connect(self._authorize_lark)
        self._lark_status = _status_label()
        self._refresh_lark_status()
        auth_row.addWidget(auth_btn)
        auth_row.addStretch()
        auth_row.addWidget(self._lark_status)
        layout.addLayout(auth_row)

        layout.addStretch()

        # Nav buttons
        nav = QHBoxLayout()
        nav.addStretch()
        nxt = _btn("Next →", primary=True)
        nxt.clicked.connect(lambda: self._go_to(1))
        nav.addWidget(nxt)
        layout.addLayout(nav)

        return page

    def _authorize_lark(self):
        app_id = self._lark_app_id.text().strip()
        secret = self._lark_secret.text().strip()
        if not app_id or not secret:
            self._lark_status.setText("⚠ Enter App ID and Secret first")
            self._lark_status.setStyleSheet("color:#FF9500; font-size:11px; font-weight:600;")
            return
        # Save creds first
        self.config.update({"lark_app_id": app_id, "lark_app_secret": secret})

        # Launch OAuth in browser
        try:
            import sys, importlib
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from sync import lark_auth
            importlib.reload(lark_auth)
            lark_auth.authorize_async(on_success=self._on_lark_auth_success,
                                      on_error=self._on_lark_auth_error)
            self._lark_status.setText("⏳ Waiting for browser…")
            self._lark_status.setStyleSheet("color:#888; font-size:11px;")
        except Exception as e:
            self._on_lark_auth_error(str(e))

    @pyqtSlot()
    def _on_lark_auth_success(self):
        self._refresh_lark_status()

    @pyqtSlot(str)
    def _on_lark_auth_error(self, msg: str):
        self._lark_status.setText(f"✕ {msg[:40]}")
        self._lark_status.setStyleSheet("color:#FF3B30; font-size:11px; font-weight:600;")

    def _refresh_lark_status(self):
        if LARK_TOKEN.exists():
            self._lark_status.setText("✓ Connected")
            self._lark_status.setStyleSheet("color:#34C759; font-size:11px; font-weight:600;")
        else:
            self._lark_status.setText("Not connected")
            self._lark_status.setStyleSheet("color:#999; font-size:11px;")

    # ── Step 2: Google Drive ──────────────────────────────────────────

    def _build_step2(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(8)

        layout.addWidget(_step_indicator(2))

        title_row = QHBoxLayout()
        title_row.addWidget(_label("Connect Google Drive", bold=True, size=15))
        help_panel = _help_panel([
            'Go to <a href="https://console.cloud.google.com">console.cloud.google.com</a>',
            "Enable <b>Google Drive API</b>",
            "Create <b>OAuth 2.0 Client ID</b> → type: <b>Desktop app</b>",
            "Download JSON → rename to <b>credentials.json</b>",
            "Add your email as a <b>Test User</b> under OAuth consent screen → Audience",
        ])
        title_row.addStretch()
        title_row.addWidget(_help_btn("How to set up", help_panel))
        layout.addLayout(title_row)
        layout.addWidget(_label("Upload credentials.json from Google Cloud Console.", color="#888", size=11))
        layout.addWidget(help_panel)

        # credentials.json picker
        layout.addWidget(_label("credentials.json", bold=True, size=11, color="#555"))
        file_row = QHBoxLayout()
        self._creds_label = QLabel(
            str(GOOGLE_CREDS) if GOOGLE_CREDS.exists() else "No file selected"
        )
        self._creds_label.setStyleSheet(
            f"color:{'#34C759' if GOOGLE_CREDS.exists() else '#999'}; font-size:11px;"
            "border:1px solid #d0d0d0; border-radius:7px; padding:7px 10px;"
            "background:#fafafa;"
        )
        browse_btn = _btn("Browse", small=True)
        browse_btn.clicked.connect(self._browse_credentials)
        file_row.addWidget(self._creds_label, 1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        layout.addWidget(_divider())

        # Folder ID field with collapsible URL hint
        folder_header = QHBoxLayout()
        folder_header.addWidget(_label("Destination Folder ID", bold=True, size=11, color="#555"))
        folder_header.addWidget(_label("(optional)", size=10, color="#999"))
        folder_header.addStretch()

        self._url_hint = QWidget()
        self._url_hint.setVisible(False)
        hint_layout = QVBoxLayout(self._url_hint)
        hint_layout.setContentsMargins(0, 4, 0, 0)
        hint_text = QLabel(
            "Open your Google Drive folder and look at the URL:\n\n"
            "drive.google.com/drive/folders/<b>1BkXxYzAbCdEfGhIjKlMnOpQ</b>\n\n"
            "Copy the highlighted part — that is your Folder ID."
        )
        hint_text.setWordWrap(True)
        hint_text.setStyleSheet(
            "background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px;"
            "padding:8px 10px; font-size:10px; color:#166534;"
        )
        hint_layout.addWidget(hint_text)

        show_hint_btn = QPushButton("Where do I find this? ▾")
        show_hint_btn.setCheckable(True)
        show_hint_btn.setStyleSheet(
            "background:transparent; border:none; color:#007AFF;"
            "font-size:10px; text-align:left; padding:0;"
        )
        show_hint_btn.toggled.connect(lambda c: (
            self._url_hint.setVisible(c),
            show_hint_btn.setText("Hide ▴" if c else "Where do I find this? ▾")
        ))

        folder_header.addWidget(show_hint_btn)
        layout.addLayout(folder_header)

        self._folder_id = _input("Paste folder ID, or leave blank for root My Drive")
        self._folder_id.setText(self.config.get("gdrive_root_folder_id", ""))
        layout.addWidget(self._folder_id)
        layout.addWidget(self._url_hint)

        # Auth button
        auth_row = QHBoxLayout()
        auth_btn = _btn("Authorize Google →")
        auth_btn.clicked.connect(self._authorize_google)
        self._google_status = _status_label()
        self._refresh_google_status()
        auth_row.addWidget(auth_btn)
        auth_row.addStretch()
        auth_row.addWidget(self._google_status)
        layout.addLayout(auth_row)

        layout.addStretch()

        nav = QHBoxLayout()
        back = _btn("Back")
        back.clicked.connect(lambda: self._go_to(0))
        nxt = _btn("Next →", primary=True)
        nxt.clicked.connect(self._step2_next)
        nav.addWidget(back)
        nav.addStretch()
        nav.addWidget(nxt)
        layout.addLayout(nav)

        return page

    def _browse_credentials(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select credentials.json", str(Path.home()),
            "JSON Files (*.json)"
        )
        if not path:
            return
        # Validate it's a Google OAuth credentials file
        import json
        try:
            with open(path) as f:
                data = json.load(f)
            if "installed" not in data and "web" not in data:
                raise ValueError("Not a valid credentials file")
        except Exception:
            self._google_status.setText("✕ Invalid credentials.json")
            self._google_status.setStyleSheet("color:#FF3B30; font-size:11px; font-weight:600;")
            return

        # Copy to app dir
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, GOOGLE_CREDS)
        self._creds_label.setText("credentials.json ✓")
        self._creds_label.setStyleSheet(
            "color:#34C759; font-size:11px; border:1px solid #d0d0d0;"
            "border-radius:7px; padding:7px 10px; background:#fafafa;"
        )

    def _authorize_google(self):
        if not GOOGLE_CREDS.exists():
            self._google_status.setText("⚠ Select credentials.json first")
            self._google_status.setStyleSheet("color:#FF9500; font-size:11px; font-weight:600;")
            return
        self._google_status.setText("⏳ Opening browser…")
        self._google_status.setStyleSheet("color:#888; font-size:11px;")
        try:
            from sync.google_client import GoogleDriveClient
            client = GoogleDriveClient(str(GOOGLE_CREDS), str(GOOGLE_TOKEN))
            client.get_service()  # triggers OAuth flow
            self._refresh_google_status()
        except Exception as e:
            self._google_status.setText(f"✕ {str(e)[:40]}")
            self._google_status.setStyleSheet("color:#FF3B30; font-size:11px; font-weight:600;")

    def _refresh_google_status(self):
        if GOOGLE_TOKEN.exists():
            self._google_status.setText("✓ Connected")
            self._google_status.setStyleSheet("color:#34C759; font-size:11px; font-weight:600;")
        else:
            self._google_status.setText("Not connected")
            self._google_status.setStyleSheet("color:#999; font-size:11px;")

    def _step2_next(self):
        folder_id = self._folder_id.text().strip()
        self.config.set("gdrive_root_folder_id", folder_id)
        self._go_to(2)

    # ── Step 3: Preferences ───────────────────────────────────────────

    def _build_step3(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(8)

        layout.addWidget(_step_indicator(3))
        layout.addWidget(_label("Sync Preferences", bold=True, size=15))
        layout.addWidget(_label("Configure how and when to sync.", color="#888", size=11))

        # Schedule
        layout.addWidget(_label("Sync Schedule", bold=True, size=11, color="#555"))
        self._schedule_combo = QComboBox()
        self._schedule_combo.addItems(["Every week (recommended)", "Every day", "Manual only"])
        self._schedule_combo.setStyleSheet(
            "border:1px solid #d0d0d0; border-radius:7px; padding:6px 10px;"
            "font-size:12px; background:#fafafa;"
        )
        current_sched = self.config.get("schedule", "weekly")
        idx = {"weekly": 0, "daily": 1, "manual": 2}.get(current_sched, 0)
        self._schedule_combo.setCurrentIndex(idx)
        self._schedule_combo.currentIndexChanged.connect(self._on_schedule_changed)
        layout.addWidget(self._schedule_combo)

        # Day + time row (only for weekly)
        self._day_time_widget = QWidget()
        dt_row = QHBoxLayout(self._day_time_widget)
        dt_row.setContentsMargins(0, 0, 0, 0)
        dt_row.setSpacing(8)

        self._day_combo = QComboBox()
        self._day_combo.addItems(DAYS)
        self._day_combo.setCurrentText(self.config.get("schedule_day", "Monday"))
        self._day_combo.setStyleSheet(
            "border:1px solid #d0d0d0; border-radius:7px; padding:6px 10px;"
            "font-size:12px; background:#fafafa;"
        )

        self._hour_combo = QComboBox()
        self._hour_combo.addItems(HOURS)
        self._hour_combo.setCurrentIndex(self.config.get("schedule_hour", 8))
        self._hour_combo.setStyleSheet(
            "border:1px solid #d0d0d0; border-radius:7px; padding:6px 10px;"
            "font-size:12px; background:#fafafa;"
        )

        dt_row.addWidget(_label("Run on", size=11, color="#555"))
        dt_row.addWidget(self._day_combo, 1)
        dt_row.addWidget(self._hour_combo, 1)
        layout.addWidget(self._day_time_widget)

        layout.addWidget(_divider())

        # Conflict resolution
        layout.addWidget(_label("If file already exists in Google Drive", bold=True, size=11, color="#555"))
        self._conflict_combo = QComboBox()
        self._conflict_combo.addItems(["Overwrite (always use latest version)", "Skip (keep existing)"])
        self._conflict_combo.setStyleSheet(
            "border:1px solid #d0d0d0; border-radius:7px; padding:6px 10px;"
            "font-size:12px; background:#fafafa;"
        )
        conflict = self.config.get("conflict", "overwrite")
        self._conflict_combo.setCurrentIndex(0 if conflict == "overwrite" else 1)
        layout.addWidget(self._conflict_combo)

        layout.addWidget(_divider())

        # Notification chat ID (optional)
        layout.addWidget(_label("Lark Notification Group Chat ID", bold=True, size=11, color="#555"))
        self._notify_id = _input("Optional — paste Lark group chat_id")
        self._notify_id.setText(self.config.get("lark_notify_chat_id", ""))
        layout.addWidget(self._notify_id)
        layout.addWidget(_label(
            "Run find_chat_id.py to get the chat_id for your group.",
            size=10, color="#999"
        ))

        layout.addStretch()

        nav = QHBoxLayout()
        back = _btn("Back")
        back.clicked.connect(lambda: self._go_to(1))
        nxt = _btn("Next →", primary=True)
        nxt.clicked.connect(self._step3_next)
        nav.addWidget(back)
        nav.addStretch()
        nav.addWidget(nxt)
        layout.addLayout(nav)

        self._on_schedule_changed(idx)
        return page

    def _on_schedule_changed(self, idx: int):
        self._day_time_widget.setVisible(idx == 0)  # weekly only

    def _step3_next(self):
        sched_map = {0: "weekly", 1: "daily", 2: "manual"}
        self.config.update({
            "schedule":           sched_map[self._schedule_combo.currentIndex()],
            "schedule_day":       self._day_combo.currentText(),
            "schedule_hour":      self._hour_combo.currentIndex(),
            "conflict":           "overwrite" if self._conflict_combo.currentIndex() == 0 else "skip",
            "lark_notify_chat_id": self._notify_id.text().strip(),
        })
        self._go_to(3)

    # ── Step 4: Done ─────────────────────────────────────────────────

    def _build_step4(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(8)

        layout.addWidget(_step_indicator(4))
        layout.addStretch()

        check = _label("✅", size=36)
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(check)

        title = _label("All set!", bold=True, size=16)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._done_sub = _label("", color="#888", size=11)
        self._done_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_sub.setWordWrap(True)
        layout.addWidget(self._done_sub)

        # Summary box
        self._summary_box = QLabel()
        self._summary_box.setWordWrap(True)
        self._summary_box.setStyleSheet(
            "background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px;"
            "padding:12px; font-size:11px; color:#374151;"
        )
        layout.addWidget(self._summary_box)
        layout.addStretch()

        start_btn = _btn("Start LarkSync", primary=True)
        start_btn.setFixedHeight(38)
        start_btn.clicked.connect(self._finish)
        layout.addWidget(start_btn)

        return page

    def _update_done_page(self):
        sched = self.config.get("schedule", "weekly")
        day   = self.config.get("schedule_day", "Monday")
        hour  = self.config.get("schedule_hour", 8)
        hstr  = HOURS[hour] if hour < len(HOURS) else f"{hour:02d}:00"

        if sched == "weekly":
            sched_str = f"Every {day} at {hstr}"
        elif sched == "daily":
            sched_str = f"Every day at {hstr}"
        else:
            sched_str = "Manual only"

        self._done_sub.setText(f"LarkSync will run {sched_str.lower()}.")
        conflict = "Overwrite existing files" if self.config.get("conflict") == "overwrite" else "Skip existing files"
        self._summary_box.setText(
            f"<b>Direction:</b> Lark Drive → Google Drive<br>"
            f"<b>Scope:</b> All files & folders<br>"
            f"<b>Format:</b> Google native (Docs, Sheets, Slides)<br>"
            f"<b>Schedule:</b> {sched_str}<br>"
            f"<b>Conflict:</b> {conflict}"
        )

    def _go_to(self, idx: int):
        if idx == 3:
            self._update_done_page()
        self._stack.setCurrentIndex(idx)

    def _finish(self):
        self.config.mark_setup_complete()
        self.accept()

    # ── Footer ────────────────────────────────────────────────────────

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(28)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(FOOTER_TEXT)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {_c('#666666','#888888')}; font-size: 10px;"
            f"border-top: 1px solid {_c('#f0f0f0','#3a3a3c')}; padding-top: 4px;"
        )
        layout.addWidget(lbl)
        return w
