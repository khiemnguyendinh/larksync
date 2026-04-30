"""
Settings Dialog
Tabbed settings panel accessible from the tray menu.
Tabs: General | Lark | Google Drive | Notifications
"""

from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTabWidget, QWidget, QCheckBox,
    QFrame, QFileDialog, QSizePolicy
)
from pathlib import Path
import shutil

from app.config_manager import (
    ConfigManager, APP_DIR, GOOGLE_CREDS, LARK_TOKEN, GOOGLE_TOKEN
)

FOOTER_TEXT = "Sponsored by Kstudy Academy · www.kstudy.edu.vn"
DAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
HOURS = [f"{h:02d}:00 {'AM' if h < 12 else 'PM'}" for h in range(24)]


def _dark() -> bool:
    from PyQt6.QtWidgets import QApplication
    return QApplication.palette().window().color().lightness() < 128

def _c(light: str, dark: str) -> str:
    return dark if _dark() else light


def _label(text, bold=False, color=None, size=12) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    f = lbl.font(); f.setPointSize(size); f.setBold(bold)
    lbl.setFont(f)
    _adaptive = {"#1a1a1a": _c("#1a1a1a","#e5e5e5"),
                 "#888":    _c("#888888","#aaaaaa"),
                 "#999":    _c("#999999","#aaaaaa"),
                 "#555":    _c("#555555","#aaaaaa"),
                 "#666":    _c("#666666","#999999"),
                 None:      _c("#1a1a1a","#e5e5e5")}
    lbl.setStyleSheet(f"color:{_adaptive.get(color, color)};")
    return lbl

def _input(placeholder="", password=False) -> QLineEdit:
    e = QLineEdit(); e.setPlaceholderText(placeholder)
    if password: e.setEchoMode(QLineEdit.EchoMode.Password)
    border = _c("#d0d0d0","#444444")
    bg     = _c("#fafafa","#2c2c2e")
    fg     = _c("#333333","#e0e0e0")
    e.setStyleSheet(f"""
        QLineEdit {{ border:1px solid {border}; border-radius:7px;
            padding:7px 10px; font-size:12px; background:{bg}; color:{fg}; }}
        QLineEdit:focus {{ border-color:#007AFF; }}
    """)
    return e

def _combo(items) -> QComboBox:
    c = QComboBox(); c.addItems(items)
    border = _c("#d0d0d0","#444444")
    bg     = _c("#fafafa","#2c2c2e")
    fg     = _c("#333333","#e0e0e0")
    c.setStyleSheet(
        f"border:1px solid {border}; border-radius:7px;"
        f"padding:6px 10px; font-size:12px; background:{bg}; color:{fg};"
    )
    return c

def _divider() -> QFrame:
    l = QFrame(); l.setFrameShape(QFrame.Shape.HLine)
    l.setStyleSheet(f"color:{_c('#e0e0e0','#3a3a3c')};"); return l

def _btn(text, primary=False) -> QPushButton:
    b = QPushButton(text)
    if primary:
        b.setStyleSheet("""
            QPushButton { background:#007AFF; color:white; border:none;
                border-radius:7px; padding:7px 18px; font-size:12px; font-weight:600; }
            QPushButton:hover { background:#0066DD; }
        """)
    else:
        btn_bg = _c("#ffffff","#3a3a3c")
        b.setStyleSheet(f"""
            QPushButton {{ background:{btn_bg}; color:#007AFF;
                border:1px solid #007AFF; border-radius:7px;
                padding:7px 18px; font-size:12px; font-weight:600; }}
            QPushButton:hover {{ background:rgba(0,122,255,0.12); }}
        """)
    return b

def _setting_row(label: str, sub: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    text_col = QVBoxLayout()
    text_col.setSpacing(1)
    text_col.addWidget(_label(label, bold=True, size=12))
    if sub:
        text_col.addWidget(_label(sub, color="#999", size=10))
    row.addLayout(text_col, 1)
    row.addWidget(widget)
    return row


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("LarkSync Settings")
        self.setFixedSize(480, 520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tab_bg   = _c("#ffffff", "#1c1c1e")
        tab_fg   = _c("#444444", "#aaaaaa")
        tab_pane = _c("#f5f5f5", "#2c2c2e")
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background:{tab_pane}; }}
            QTabBar::tab {{ padding: 8px 16px; font-size: 12px;
                background:{tab_bg}; color:{tab_fg}; }}
            QTabBar::tab:selected {{ color:#007AFF;
                border-bottom:2px solid #007AFF; }}
        """)
        tabs.addTab(self._general_tab(),    "General")
        tabs.addTab(self._lark_tab(),       "Lark")
        tabs.addTab(self._gdrive_tab(),     "Google Drive")
        tabs.addTab(self._notify_tab(),     "Notifications")

        root.addWidget(tabs, 1)

        # Buttons
        bar_bg  = _c("#ffffff", "#1c1c1e")
        bar_sep = _c("#f0f0f0", "#3a3a3c")
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"border-top:1px solid {bar_sep}; background:{bar_bg};")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(16, 10, 16, 10)
        cancel = _btn("Cancel")
        cancel.clicked.connect(self.reject)
        save = _btn("Save Changes", primary=True)
        save.clicked.connect(self._save)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        root.addWidget(btn_bar)

        root.addWidget(self._footer())

    # ── General tab ───────────────────────────────────────────────────

    def _general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Launch at login
        self._launch_cb = QCheckBox()
        self._launch_cb.setChecked(self.config.get("launch_at_login", False))
        layout.addLayout(_setting_row(
            "Launch at Login",
            "Start LarkSync automatically when you log in",
            self._launch_cb
        ))
        layout.addWidget(_divider())

        # Schedule
        layout.addWidget(_label("Sync Schedule", bold=True, size=12))
        self._sched_combo = _combo(["Every week (recommended)", "Every day", "Manual only"])
        sched_idx = {"weekly":0, "daily":1, "manual":2}.get(self.config.get("schedule","weekly"), 0)
        self._sched_combo.setCurrentIndex(sched_idx)
        self._sched_combo.currentIndexChanged.connect(self._on_sched_changed)
        layout.addWidget(self._sched_combo)

        self._day_time_row = QWidget()
        dt = QHBoxLayout(self._day_time_row)
        dt.setContentsMargins(0,0,0,0); dt.setSpacing(8)
        self._day_combo = _combo(DAYS)
        self._day_combo.setCurrentText(self.config.get("schedule_day","Monday"))
        self._hour_combo = _combo(HOURS)
        self._hour_combo.setCurrentIndex(self.config.get("schedule_hour",8))
        dt.addWidget(_label("Run on", size=11, color="#555"))
        dt.addWidget(self._day_combo, 1)
        dt.addWidget(self._hour_combo, 1)
        layout.addWidget(self._day_time_row)
        layout.addWidget(_divider())

        # Conflict
        layout.addWidget(_label("If file already exists", bold=True, size=12))
        self._conflict_combo = _combo([
            "Overwrite (always use latest version)",
            "Skip (keep existing)"
        ])
        self._conflict_combo.setCurrentIndex(
            0 if self.config.get("conflict","overwrite") == "overwrite" else 1
        )
        layout.addWidget(self._conflict_combo)
        layout.addStretch()

        self._on_sched_changed(sched_idx)
        return w

    def _on_sched_changed(self, idx):
        self._day_time_row.setVisible(idx == 0)

    # ── Lark tab ──────────────────────────────────────────────────────

    def _lark_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(_label("App ID", bold=True, size=11, color="#555"))
        self._lark_id_edit = _input("cli_xxx...")
        self._lark_id_edit.setText(self.config.get("lark_app_id",""))
        layout.addWidget(self._lark_id_edit)

        layout.addWidget(_label("App Secret", bold=True, size=11, color="#555"))
        self._lark_sec_edit = _input("App Secret", password=True)
        self._lark_sec_edit.setText(self.config.get("lark_app_secret",""))
        layout.addWidget(self._lark_sec_edit)

        layout.addWidget(_divider())

        status_row = QHBoxLayout()
        self._lark_status = _label(
            "✓ Connected" if LARK_TOKEN.exists() else "Not connected",
            color="#34C759" if LARK_TOKEN.exists() else "#999", size=11
        )
        re_auth = _btn("Re-authorize Lark")
        re_auth.clicked.connect(self._reauth_lark)
        status_row.addWidget(self._lark_status)
        status_row.addStretch()
        status_row.addWidget(re_auth)
        layout.addLayout(status_row)
        layout.addStretch()
        return w

    def _reauth_lark(self):
        app_id = self._lark_id_edit.text().strip()
        secret = self._lark_sec_edit.text().strip()
        if not app_id or not secret:
            self._lark_status.setText("⚠ Enter App ID and Secret first")
            self._lark_status.setStyleSheet("color:#FF9500; font-size:11px;")
            return
        self.config.update({"lark_app_id": app_id, "lark_app_secret": secret})
        try:
            from sync.lark_auth import authorize
            authorize()
            self._lark_status.setText("✓ Connected")
            self._lark_status.setStyleSheet("color:#34C759; font-size:11px; font-weight:600;")
        except Exception as e:
            self._lark_status.setText(f"✕ {str(e)[:50]}")
            self._lark_status.setStyleSheet("color:#FF3B30; font-size:11px;")

    # ── Google Drive tab ──────────────────────────────────────────────

    def _gdrive_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(_label("credentials.json", bold=True, size=11, color="#555"))
        file_row = QHBoxLayout()
        _creds_ok = GOOGLE_CREDS.exists()
        self._creds_lbl = QLabel(
            "credentials.json ✓" if _creds_ok else "No file selected"
        )
        _cred_fg  = "#34C759" if _creds_ok else _c("#999999","#aaaaaa")
        _cred_bdr = _c("#d0d0d0","#444444")
        _cred_bg  = _c("#fafafa","#2c2c2e")
        self._creds_lbl.setStyleSheet(
            f"color:{_cred_fg}; font-size:11px; border:1px solid {_cred_bdr};"
            f"border-radius:7px; padding:7px 10px; background:{_cred_bg};"
        )
        browse = _btn("Browse")
        browse.clicked.connect(self._browse_creds)
        file_row.addWidget(self._creds_lbl, 1)
        file_row.addWidget(browse)
        layout.addLayout(file_row)

        layout.addWidget(_label("Destination Folder ID", bold=True, size=11, color="#555"))
        self._folder_edit = _input("Folder ID or leave blank for root")
        self._folder_edit.setText(self.config.get("gdrive_root_folder_id",""))
        layout.addWidget(self._folder_edit)

        layout.addWidget(_label(
            "Get ID from URL: drive.google.com/drive/folders/<b>FOLDER_ID</b>",
            color="#999", size=10
        ))

        layout.addWidget(_divider())

        status_row = QHBoxLayout()
        self._google_status = _label(
            "✓ Connected" if GOOGLE_TOKEN.exists() else "Not connected",
            color="#34C759" if GOOGLE_TOKEN.exists() else "#999", size=11
        )
        re_auth = _btn("Re-authorize Google")
        re_auth.clicked.connect(self._reauth_google)
        status_row.addWidget(self._google_status)
        status_row.addStretch()
        status_row.addWidget(re_auth)
        layout.addLayout(status_row)
        layout.addStretch()
        return w

    def _browse_creds(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select credentials.json", str(Path.home()), "JSON Files (*.json)"
        )
        if not path: return
        import json
        try:
            with open(path) as f:
                data = json.load(f)
            if "installed" not in data and "web" not in data:
                raise ValueError()
        except Exception:
            self._google_status.setText("✕ Invalid credentials.json")
            self._google_status.setStyleSheet("color:#FF3B30; font-size:11px;")
            return
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, GOOGLE_CREDS)
        self._creds_lbl.setText("credentials.json ✓")
        _bdr = _c("#d0d0d0","#444444"); _bg = _c("#fafafa","#2c2c2e")
        self._creds_lbl.setStyleSheet(
            f"color:#34C759; font-size:11px; border:1px solid {_bdr};"
            f"border-radius:7px; padding:7px 10px; background:{_bg};"
        )

    def _reauth_google(self):
        if not GOOGLE_CREDS.exists():
            self._google_status.setText("⚠ Select credentials.json first")
            return
        try:
            from sync.google_client import GoogleDriveClient
            GoogleDriveClient(str(GOOGLE_CREDS), str(GOOGLE_TOKEN)).get_service()
            self._google_status.setText("✓ Connected")
            self._google_status.setStyleSheet("color:#34C759; font-size:11px; font-weight:600;")
        except Exception as e:
            self._google_status.setText(f"✕ {str(e)[:50]}")
            self._google_status.setStyleSheet("color:#FF3B30; font-size:11px;")

    # ── Notifications tab ─────────────────────────────────────────────

    def _notify_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(_label(
            "Get notified in your Lark group chat after each sync.",
            color="#888", size=11
        ))

        layout.addWidget(_label("Lark Group Chat ID", bold=True, size=11, color="#555"))
        self._notify_edit = _input("oc_xxxxxxxxxxxxxxxx")
        self._notify_edit.setText(self.config.get("lark_notify_chat_id",""))
        layout.addWidget(self._notify_edit)

        layout.addWidget(_label(
            "Run find_chat_id.py in your lark_gdrive_sync folder to find this ID.",
            color="#999", size=10
        ))
        layout.addStretch()
        return w

    # ── Save ──────────────────────────────────────────────────────────

    def _save(self):
        sched_map = {0:"weekly", 1:"daily", 2:"manual"}
        updates = {
            "launch_at_login":    self._launch_cb.isChecked(),
            "schedule":           sched_map[self._sched_combo.currentIndex()],
            "schedule_day":       self._day_combo.currentText(),
            "schedule_hour":      self._hour_combo.currentIndex(),
            "conflict":           "overwrite" if self._conflict_combo.currentIndex()==0 else "skip",
            "lark_app_id":        self._lark_id_edit.text().strip(),
            "lark_app_secret":    self._lark_sec_edit.text().strip(),
            "gdrive_root_folder_id": self._folder_edit.text().strip(),
            "lark_notify_chat_id":   self._notify_edit.text().strip(),
        }
        self.config.update(updates)

        if updates["launch_at_login"] != self.config.get("launch_at_login"):
            self.config.set_launch_at_login(updates["launch_at_login"])

        self.accept()

    # ── Footer ────────────────────────────────────────────────────────

    def _footer(self) -> QWidget:
        w = QWidget(); w.setFixedHeight(26)
        layout = QHBoxLayout(w); layout.setContentsMargins(0,0,0,0)
        lbl = QLabel(FOOTER_TEXT)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fg  = _c("#888888", "#666666")
        sep = _c("#f0f0f0", "#3a3a3c")
        lbl.setStyleSheet(f"color:{fg}; font-size:10px; border-top:1px solid {sep}; padding-top:4px;")
        layout.addWidget(lbl)
        return w
