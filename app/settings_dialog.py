"""
Settings Dialog
Tabbed settings panel accessible from the tray menu.
Tabs: General | Larksuite | Google Drive | Notifications
"""

from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTabWidget, QWidget, QCheckBox,
    QFrame, QFileDialog, QSizePolicy, QScrollArea
)
from pathlib import Path
import shutil

from app.config_manager import (
    ConfigManager, APP_DIR, GOOGLE_CREDS, LARK_TOKEN, GOOGLE_TOKEN
)

FOOTER_TEXT = "© 2026 Khiem Nguyen Dinh · Kstudy Academy · www.kstudy.edu.vn"
DAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
HOURS = [f"{h:02d}:00 {'AM' if h < 12 else 'PM'}" for h in range(24)]


# ── Theme helpers ────────────────────────────────────────────────────

def _dark() -> bool:
    from PyQt6.QtWidgets import QApplication
    return QApplication.palette().window().color().lightness() < 128

def _c(light: str, dark: str) -> str:
    return dark if _dark() else light


# ── Shared widget factories ──────────────────────────────────────────

def _label(text, bold=False, color=None, size=12) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    f = lbl.font(); f.setPointSize(size); f.setBold(bold); lbl.setFont(f)
    _map = {
        "#1a1a1a": _c("#1a1a1a","#e5e5e5"),
        "#888":    _c("#888888","#aaaaaa"),
        "#999":    _c("#999999","#aaaaaa"),
        "#555":    _c("#555555","#bbbbbb"),
        "#666":    _c("#666666","#999999"),
        None:      _c("#1a1a1a","#e5e5e5"),
    }
    resolved = _map.get(color, color)
    lbl.setStyleSheet(f"color: {resolved}; background: transparent; border: none;")
    return lbl


def _input(placeholder="", password=False) -> QLineEdit:
    e = QLineEdit(); e.setPlaceholderText(placeholder)
    if password: e.setEchoMode(QLineEdit.EchoMode.Password)
    bdr = _c("#d0d0d0","#555555")
    bg  = _c("#ffffff","#2c2c2e")
    fg  = _c("#333333","#e0e0e0")
    e.setStyleSheet(f"""
        QLineEdit {{
            border: 1px solid {bdr}; border-radius: 8px;
            padding: 8px 12px; font-size: 13px;
            background: {bg}; color: {fg};
        }}
        QLineEdit:focus {{ border-color: #007AFF; }}
    """)
    return e


def _combo(items) -> QComboBox:
    c = QComboBox(); c.addItems(items)
    bdr = _c("#d0d0d0","#555555")
    bg  = _c("#ffffff","#2c2c2e")
    fg  = _c("#333333","#e0e0e0")
    c.setStyleSheet(f"""
        QComboBox {{
            border: 1px solid {bdr}; border-radius: 8px;
            padding: 7px 12px; font-size: 13px;
            background: {bg}; color: {fg};
        }}
        QComboBox:focus {{ border-color: #007AFF; }}
        QComboBox::drop-down {{ border: none; width: 24px; }}
    """)
    return c


def _divider() -> QFrame:
    d = QFrame(); d.setFrameShape(QFrame.Shape.HLine)
    d.setStyleSheet(f"color: {_c('#e8e8e8','#3a3a3c')}; border: none;")
    d.setFixedHeight(1)
    return d


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    f = lbl.font(); f.setPointSize(11); f.setBold(True); lbl.setFont(f)
    fg = _c("#555555", "#bbbbbb")
    lbl.setStyleSheet(
        f"color: {fg}; background: transparent; border: none;"
        "text-transform: uppercase; letter-spacing: 1px; padding-top: 4px;"
    )
    return lbl


def _setting_row(label: str, sub: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    text_col = QVBoxLayout(); text_col.setSpacing(2)
    text_col.addWidget(_label(label, bold=True, size=12))
    if sub:
        text_col.addWidget(_label(sub, color="#999", size=10))
    row.addLayout(text_col, 1)
    row.addWidget(widget)
    return row


# ── Secure input field (password mode + eye toggle) ──────────────────

class _SecretField(QWidget):
    """
    A QLineEdit that defaults to password-echo mode with a 👁 button on the
    right that toggles visibility.  Exposes the same .text() / .setText() /
    .textChanged API as a plain QLineEdit so it can be used as a drop-in.
    """

    def __init__(self, placeholder: str = ""):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._edit = _input(placeholder, password=True)

        bdr   = _c("#d0d0d0", "#555555")
        bg    = _c("#f5f5f7", "#2c2c2e")
        fg    = _c("#888888", "#aaaaaa")
        hover = _c("#e8e8e8", "#3a3a3c")
        act   = _c("#ddeeff", "#1a2a3a")

        self._eye = QPushButton("👁")
        self._eye.setFixedSize(36, 36)
        self._eye.setCheckable(True)
        self._eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self._eye.setToolTip("Show / hide")
        self._eye.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {fg};
                border: 1px solid {bdr}; border-radius: 8px;
                font-size: 15px; padding: 0;
            }}
            QPushButton:hover   {{ background: {hover}; }}
            QPushButton:checked {{ color: #007AFF; background: {act}; }}
        """)
        self._eye.toggled.connect(
            lambda on: self._edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )

        row.addWidget(self._edit, 1)
        row.addWidget(self._eye)

    # ── Proxy API ──────────────────────────────────────────────────────
    def text(self) -> str:        return self._edit.text()
    def setText(self, t: str):    self._edit.setText(t)

    @property
    def textChanged(self):
        """Return the inner QLineEdit's textChanged signal so callers can connect."""
        return self._edit.textChanged


# ── Main dialog ──────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, tray_app=None, parent=None):
        super().__init__(parent)  # parent must be QWidget or None
        self.config = config
        self._tray_app = tray_app  # stored separately, not as Qt parent
        self.setWindowTitle("LarkSync Settings")
        self.setFixedSize(520, 560)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        # Dialog background
        win_bg = _c("#f5f5f7", "#1c1c1e")
        self.setStyleSheet(f"QDialog {{ background: {win_bg}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Tab widget ────────────────────────────────────────────────
        tabs = QTabWidget()

        # Tab styling — explicit colors so text is always visible
        pane_bg  = _c("#ffffff", "#2c2c2e")
        bar_bg   = _c("#f5f5f7", "#1c1c1e")
        tab_fg   = _c("#666666", "#999999")
        sel_fg   = "#007AFF"
        sel_bar  = "#007AFF"
        hover_bg = _c("#e8e8ed", "#3a3a3c")

        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {pane_bg};
                border-top: 1px solid {_c('#e0e0e0','#3a3a3c')};
            }}
            QTabBar {{
                background: {bar_bg};
            }}
            QTabBar::tab {{
                padding: 10px 18px;
                margin: 0px;
                font-size: 13px;
                font-weight: 500;
                color: {tab_fg};
                background: {bar_bg};
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 80px;
            }}
            QTabBar::tab:hover {{
                color: {_c('#333333','#cccccc')};
                background: {hover_bg};
            }}
            QTabBar::tab:selected {{
                color: {sel_fg};
                border-bottom: 2px solid {sel_bar};
                font-weight: 600;
            }}
        """)

        tabs.addTab(self._general_tab(),  "  General  ")
        tabs.addTab(self._lark_tab(),     "  Larksuite  ")
        tabs.addTab(self._gdrive_tab(),   "  Google Drive  ")
        tabs.addTab(self._notify_tab(),   "  Notifications  ")

        root.addWidget(tabs, 1)

        # ── Bottom button bar ─────────────────────────────────────────
        btn_bar = QWidget()
        btn_bg = _c("#f5f5f7", "#1c1c1e")
        btn_sep = _c("#e0e0e0", "#3a3a3c")
        btn_bar.setStyleSheet(
            f"background: {btn_bg}; border-top: 1px solid {btn_sep};"
        )
        btn_layout = QVBoxLayout(btn_bar)
        btn_layout.setContentsMargins(20, 10, 20, 10)
        btn_layout.setSpacing(6)

        # Status label (Syncing... / empty)
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(
            "color: #007AFF; font-size: 12px; font-weight: 500;"
            "background: transparent; border: none;"
        )
        self._status_lbl.setFixedHeight(16)
        btn_layout.addWidget(self._status_lbl)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._cancel_btn = self._make_btn("Cancel", primary=False)
        self._cancel_btn.clicked.connect(self.reject)
        self._cancel_btn.setEnabled(False)
        self._set_cancel_dimmed(True)

        self._sync_btn = self._make_btn("Sync Now", primary=True)
        self._sync_btn.clicked.connect(self._on_sync_btn_clicked)

        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addSpacing(4)
        btn_row.addWidget(self._sync_btn)
        btn_layout.addLayout(btn_row)

        root.addWidget(btn_bar)

        # ── Footer ────────────────────────────────────────────────────
        root.addWidget(self._footer())

        # Connect change signals after all widgets are built
        self._connect_change_signals()

    # ── Button helpers ────────────────────────────────────────────────

    def _set_cancel_dimmed(self, dimmed: bool):
        if dimmed:
            fg  = _c("#cccccc", "#555555")
            bdr = _c("#e8e8e8", "#3a3a3c")
            bg  = _c("#f5f5f7", "#2a2a2c")
            self._cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {fg};
                    border: 1px solid {bdr}; border-radius: 8px;
                    padding: 0 20px; font-size: 13px; font-weight: 500;
                }}
            """)
            self._cancel_btn.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            bg  = _c("#ffffff", "#3a3a3c")
            bdr = _c("#d0d0d0", "#555555")
            fg  = _c("#333333", "#e0e0e0")
            self._cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {fg};
                    border: 1px solid {bdr}; border-radius: 8px;
                    padding: 0 20px; font-size: 13px; font-weight: 500;
                }}
                QPushButton:hover {{ background: {_c('#f0f0f0','#4a4a4c')}; }}
                QPushButton:pressed {{ background: {_c('#e0e0e0','#555555')}; }}
            """)
            self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_input_changed(self):
        self._cancel_btn.setEnabled(True)
        self._set_cancel_dimmed(False)

    def _connect_change_signals(self):
        for w in [self._lark_id_edit, self._lark_sec_edit,
                  self._folder_edit, self._notify_edit]:
            w.textChanged.connect(self._on_input_changed)
        for w in [self._sched_combo, self._day_combo, self._hour_combo,
                  self._sync_mode_combo, self._conflict_combo]:
            w.currentIndexChanged.connect(self._on_input_changed)
        self._launch_cb.stateChanged.connect(self._on_input_changed)

    # ── Button factory ────────────────────────────────────────────────

    @staticmethod
    def _make_btn(text: str, primary: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(34)
        if primary:
            b.setStyleSheet("""
                QPushButton {
                    background: #007AFF; color: white; border: none;
                    border-radius: 8px; padding: 0 24px;
                    font-size: 13px; font-weight: 600;
                }
                QPushButton:hover { background: #0066DD; }
                QPushButton:pressed { background: #0055CC; }
            """)
        else:
            bg  = _c("#ffffff", "#3a3a3c")
            bdr = _c("#d0d0d0", "#555555")
            fg  = _c("#333333", "#e0e0e0")
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {fg};
                    border: 1px solid {bdr}; border-radius: 8px;
                    padding: 0 20px; font-size: 13px; font-weight: 500;
                }}
                QPushButton:hover {{ background: {_c('#f0f0f0','#4a4a4c')}; }}
                QPushButton:pressed {{ background: {_c('#e0e0e0','#555555')}; }}
            """)
        return b

    # ── General tab ───────────────────────────────────────────────────

    def _general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

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
        layout.addWidget(_section_title("Sync Schedule"))
        self._sched_combo = _combo(["Every week (recommended)", "Every day", "Manual only"])
        sched_idx = {"weekly":0, "daily":1, "manual":2}.get(
            self.config.get("schedule","weekly"), 0
        )
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

        # Sync mode
        layout.addWidget(_section_title("Sync Mode"))
        self._sync_mode_combo = _combo([
            "Incremental (only new & modified since last sync)",
            "Full sync (all files every time)"
        ])
        self._sync_mode_combo.setCurrentIndex(
            0 if self.config.get("sync_mode", "incremental") == "incremental" else 1
        )
        layout.addWidget(self._sync_mode_combo)
        layout.addWidget(_label(
            "Incremental sync is faster — only files created or modified "
            "after the last sync will be processed.",
            color="#999", size=10
        ))
        layout.addWidget(_divider())

        # Conflict
        layout.addWidget(_section_title("Existing Files"))
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

    # ── Larksuite tab ─────────────────────────────────────────────────

    def _lark_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        layout.addWidget(_section_title("Lark App Credentials"))
        layout.addWidget(_label("App ID", bold=True, size=12, color="#555"))
        self._lark_id_edit = _SecretField("cli_xxx...")
        self._lark_id_edit.setText(self.config.get("lark_app_id",""))
        layout.addWidget(self._lark_id_edit)

        layout.addWidget(_label("App Secret", bold=True, size=12, color="#555"))
        self._lark_sec_edit = _SecretField("App Secret")
        self._lark_sec_edit.setText(self.config.get("lark_app_secret",""))
        layout.addWidget(self._lark_sec_edit)

        layout.addWidget(_divider())

        layout.addWidget(_section_title("Connection Status"))
        status_row = QHBoxLayout()
        self._lark_status = _label(
            "✓ Connected" if LARK_TOKEN.exists() else "⬤ Not connected",
            color="#34C759" if LARK_TOKEN.exists() else "#999", size=12
        )
        re_auth = self._make_btn("Re-authorize Lark")
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
            self._lark_status.setStyleSheet(
                "color: #FF9500; font-size: 12px; background: transparent; border: none;"
            )
            return
        self.config.update({"lark_app_id": app_id, "lark_app_secret": secret})
        try:
            from sync.lark_auth import authorize
            authorize()
            self._lark_status.setText("✓ Connected")
            self._lark_status.setStyleSheet(
                "color: #34C759; font-size: 12px; font-weight: 600;"
                "background: transparent; border: none;"
            )
        except Exception as e:
            self._lark_status.setText(f"✕ {str(e)[:50]}")
            self._lark_status.setStyleSheet(
                "color: #FF3B30; font-size: 12px;"
                "background: transparent; border: none;"
            )

    # ── Google Drive tab ──────────────────────────────────────────────

    def _gdrive_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        layout.addWidget(_section_title("OAuth Credentials"))
        layout.addWidget(_label("credentials.json", bold=True, size=12, color="#555"))
        file_row = QHBoxLayout()
        _creds_ok = GOOGLE_CREDS.exists()
        self._creds_lbl = QLabel(
            "credentials.json ✓" if _creds_ok else "No file selected"
        )
        _cred_fg  = "#34C759" if _creds_ok else _c("#999999","#aaaaaa")
        _cred_bdr = _c("#d0d0d0","#555555")
        _cred_bg  = _c("#ffffff","#2c2c2e")
        self._creds_lbl.setStyleSheet(
            f"color: {_cred_fg}; font-size: 12px; border: 1px solid {_cred_bdr};"
            f"border-radius: 8px; padding: 8px 12px; background: {_cred_bg};"
        )
        browse = self._make_btn("Browse")
        browse.clicked.connect(self._browse_creds)
        file_row.addWidget(self._creds_lbl, 1)
        file_row.addWidget(browse)
        layout.addLayout(file_row)

        layout.addWidget(_divider())

        layout.addWidget(_section_title("Destination"))
        layout.addWidget(_label("Google Drive Folder ID", bold=True, size=12, color="#555"))
        self._folder_edit = _SecretField("Folder ID or leave blank for root")
        self._folder_edit.setText(self.config.get("gdrive_root_folder_id",""))
        layout.addWidget(self._folder_edit)
        layout.addWidget(_label(
            "Get the ID from your browser URL: "
            "drive.google.com/drive/folders/<b>THIS_IS_THE_ID</b>",
            color="#999", size=10
        ))

        layout.addWidget(_divider())

        layout.addWidget(_section_title("Connection Status"))
        status_row = QHBoxLayout()
        self._google_status = _label(
            "✓ Connected" if GOOGLE_TOKEN.exists() else "⬤ Not connected",
            color="#34C759" if GOOGLE_TOKEN.exists() else "#999", size=12
        )
        re_auth = self._make_btn("Re-authorize Google")
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
            self._google_status.setStyleSheet(
                "color: #FF3B30; font-size: 12px;"
                "background: transparent; border: none;"
            )
            return
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, GOOGLE_CREDS)
        self._creds_lbl.setText("credentials.json ✓")
        bdr = _c("#d0d0d0","#555555"); bg = _c("#ffffff","#2c2c2e")
        self._creds_lbl.setStyleSheet(
            f"color: #34C759; font-size: 12px; border: 1px solid {bdr};"
            f"border-radius: 8px; padding: 8px 12px; background: {bg};"
        )

    def _reauth_google(self):
        if not GOOGLE_CREDS.exists():
            self._google_status.setText("⚠ Select credentials.json first")
            self._google_status.setStyleSheet(
                "color: #FF9500; font-size: 12px;"
                "background: transparent; border: none;"
            )
            return
        try:
            from sync.google_client import GoogleDriveClient
            GoogleDriveClient(str(GOOGLE_CREDS), str(GOOGLE_TOKEN)).get_service()
            self._google_status.setText("✓ Connected")
            self._google_status.setStyleSheet(
                "color: #34C759; font-size: 12px; font-weight: 600;"
                "background: transparent; border: none;"
            )
        except Exception as e:
            self._google_status.setText(f"✕ {str(e)[:50]}")
            self._google_status.setStyleSheet(
                "color: #FF3B30; font-size: 12px;"
                "background: transparent; border: none;"
            )

    # ── Notifications tab ─────────────────────────────────────────────

    def _notify_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        layout.addWidget(_section_title("Lark Group Notification"))
        layout.addWidget(_label(
            "Get notified in your Lark group chat after each sync completes.",
            color="#888", size=12
        ))

        layout.addWidget(_label("Lark Group Chat ID", bold=True, size=12, color="#555"))
        self._notify_edit = _SecretField("oc_xxxxxxxxxxxxxxxx")
        self._notify_edit.setText(self.config.get("lark_notify_chat_id",""))
        layout.addWidget(self._notify_edit)

        layout.addWidget(_label(
            "Run find_chat_id.py in your lark_gdrive_sync folder to find this ID.",
            color="#999", size=10
        ))
        layout.addStretch()
        return w

    # ── Save / Sync ───────────────────────────────────────────────────

    def _collect_updates(self) -> dict:
        sched_map = {0:"weekly", 1:"daily", 2:"manual"}
        return {
            "launch_at_login":       self._launch_cb.isChecked(),
            "schedule":              sched_map[self._sched_combo.currentIndex()],
            "schedule_day":          self._day_combo.currentText(),
            "schedule_hour":         self._hour_combo.currentIndex(),
            "sync_mode":             "incremental" if self._sync_mode_combo.currentIndex()==0 else "full",
            "conflict":              "overwrite" if self._conflict_combo.currentIndex()==0 else "skip",
            "lark_app_id":           self._lark_id_edit.text().strip(),
            "lark_app_secret":       self._lark_sec_edit.text().strip(),
            "gdrive_root_folder_id": self._folder_edit.text().strip(),
            "lark_notify_chat_id":   self._notify_edit.text().strip(),
        }

    def _apply_updates(self, updates: dict):
        self.config.update(updates)
        if updates["launch_at_login"] != self.config.get("launch_at_login"):
            self.config.set_launch_at_login(updates["launch_at_login"])

    def _on_sync_btn_clicked(self):
        # If currently syncing → cancel
        if self._sync_btn.text() == "Cancel Sync":
            if self._tray_app and hasattr(self._tray_app, '_cancel_sync'):
                self._tray_app._cancel_sync()
            self._restore_sync_btn()
            self._status_lbl.setText("")
            return

        # Save config
        updates = self._collect_updates()
        self._apply_updates(updates)

        # Switch button to Cancel Sync + show status
        self._sync_btn.setText("Cancel Sync")
        self._sync_btn.setStyleSheet("""
            QPushButton {
                background: #FF3B30; color: white; border: none;
                border-radius: 8px; padding: 0 24px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover  { background: #DD2A20; }
            QPushButton:pressed { background: #BB2010; }
        """)
        self._status_lbl.setText("⏳  Syncing…")
        self._cancel_btn.setEnabled(False)
        self._set_cancel_dimmed(True)

        # Trigger sync
        if self._tray_app and hasattr(self._tray_app, '_start_sync'):
            try:
                self._tray_app._start_sync()
                self._watch_sync_done()
            except Exception as e:
                import logging
                logging.error(f"Failed to start sync: {e}")
                self._restore_sync_btn()

    def _watch_sync_done(self):
        from PyQt6.QtCore import QTimer
        def _check():
            if not self._tray_app or not getattr(self._tray_app, '_syncing', False):
                self._restore_sync_btn()
            else:
                QTimer.singleShot(1000, _check)
        QTimer.singleShot(1000, _check)

    def _restore_sync_btn(self):
        self._sync_btn.setText("Sync Now")
        self._sync_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF; color: white; border: none;
                border-radius: 8px; padding: 0 24px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover  { background: #0066DD; }
            QPushButton:pressed { background: #0055CC; }
        """)
        self._status_lbl.setText("✓  Sync complete")

    # ── Footer ────────────────────────────────────────────────────────

    def _footer(self) -> QWidget:
        w = QWidget(); w.setFixedHeight(28)
        layout = QHBoxLayout(w); layout.setContentsMargins(0,0,0,0)
        lbl = QLabel(FOOTER_TEXT)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fg  = _c("#999999", "#666666")
        sep = _c("#e0e0e0", "#3a3a3c")
        lbl.setStyleSheet(
            f"color: {fg}; font-size: 10px;"
            f"border-top: 1px solid {sep}; padding-top: 5px;"
        )
        layout.addWidget(lbl)
        return w
