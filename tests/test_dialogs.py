import json

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

import app.setup_wizard as wizard_mod
import app.settings_dialog as settings_mod
from app import oauth_worker
from app.config_manager import ConfigManager, GOOGLE_CREDS, LARK_TOKEN, GOOGLE_TOKEN


class FakeWorker(QObject):
    succeeded = pyqtSignal()
    failed = pyqtSignal(str)
    instances = []

    def __init__(self, *args):
        super().__init__()
        self.started = self.cancelled = False
        FakeWorker.instances.append(self)

    def start(self): self.started = True
    def cancel(self): self.cancelled = True


@pytest.fixture(autouse=True)
def fake_workers(monkeypatch):
    FakeWorker.instances = []
    for mod in (wizard_mod, settings_mod):
        monkeypatch.setattr(mod, "LarkAuthWorker", FakeWorker)
        monkeypatch.setattr(mod, "GoogleAuthWorker", FakeWorker)


# ── Settings ──────────────────────────────────────────────────────────

def test_save_button_persists_without_starting_a_sync(qapp, monkeypatch):
    cfg = ConfigManager()
    started = []

    class Tray:
        _syncing = False
        def _start_sync(self): started.append(1)
    dlg = settings_mod.SettingsDialog(cfg, tray_app=Tray())
    dlg._sched_combo.setCurrentIndex(1)               # daily
    dlg._notify_edit.setText("oc_123")
    dlg._on_save_clicked()
    assert cfg.get("schedule") == "daily" and cfg.get("lark_notify_chat_id") == "oc_123"
    assert started == []
    assert dlg.result() == dlg.DialogCode.Accepted


def test_changing_the_schedule_rearms_it(qapp):
    cfg = ConfigManager()
    cfg.update({"schedule": "manual", "schedule_anchor": None})
    dlg = settings_mod.SettingsDialog(cfg)
    dlg._sched_combo.setCurrentIndex(0)
    dlg._apply_updates(dlg._collect_updates())
    assert cfg.get("schedule_anchor")

    anchor = cfg.get("schedule_anchor")
    dlg._apply_updates(dlg._collect_updates())        # nothing changed -> anchor untouched
    assert cfg.get("schedule_anchor") == anchor


def test_failed_login_item_change_is_reported_and_reverted(qapp, monkeypatch):
    cfg = ConfigManager()
    monkeypatch.setattr(ConfigManager, "set_launch_at_login", lambda self, v: False)
    dlg = settings_mod.SettingsDialog(cfg)
    dlg._launch_cb.setChecked(True)
    dlg._apply_updates(dlg._collect_updates())
    assert dlg._launch_cb.isChecked() is False and "login item" in dlg._status_lbl.text()


def test_lark_reauth_runs_in_background_and_updates_status(qapp):
    cfg = ConfigManager()
    dlg = settings_mod.SettingsDialog(cfg)
    dlg._lark_id_edit.setText("cli_x"); dlg._lark_sec_edit.setText("sec")
    dlg._reauth_lark()
    worker = FakeWorker.instances[-1]
    assert worker.started and not dlg._lark_reauth_btn.isEnabled()
    dlg._reauth_lark()                                # double click is ignored
    assert len(FakeWorker.instances) == 1
    worker.failed.emit("Port 8080 is in use")
    assert "Port 8080" in dlg._lark_status.text() and dlg._lark_reauth_btn.isEnabled()
    dlg._reauth_lark(); FakeWorker.instances[-1].succeeded.emit()
    assert "Connected" in dlg._lark_status.text()
    assert cfg.get("lark_app_id") == "cli_x"


def test_lark_reauth_needs_credentials_first(qapp):
    dlg = settings_mod.SettingsDialog(ConfigManager())
    dlg._reauth_lark()
    assert FakeWorker.instances == [] and "Enter App ID" in dlg._lark_status.text()


def test_closing_settings_cancels_a_pending_browser_sign_in(qapp):
    dlg = settings_mod.SettingsDialog(ConfigManager())
    dlg._lark_id_edit.setText("cli_x"); dlg._lark_sec_edit.setText("sec")
    dlg._reauth_lark()
    dlg.reject()
    assert FakeWorker.instances[-1].cancelled


def test_google_reauth_runs_in_background(qapp):
    GOOGLE_CREDS.write_text("{}")
    dlg = settings_mod.SettingsDialog(ConfigManager())
    dlg._reauth_google()
    assert FakeWorker.instances[-1].started
    FakeWorker.instances[-1].succeeded.emit()
    assert "Connected" in dlg._google_status.text()


def test_credentials_json_with_non_ascii_content_is_accepted(qapp, tmp_path, monkeypatch):
    f = tmp_path / "client.json"
    f.write_text(json.dumps({"installed": {"project_id": "Đồng-bộ"}}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(settings_mod.QFileDialog, "getOpenFileName", lambda *a, **k: (str(f), ""))
    dlg = settings_mod.SettingsDialog(ConfigManager())
    dlg._browse_creds()
    assert GOOGLE_CREDS.exists() and "✓" in dlg._creds_lbl.text()


def test_invalid_credentials_json_is_rejected(qapp, tmp_path, monkeypatch):
    f = tmp_path / "bad.json"; f.write_text('{"nope": 1}')
    monkeypatch.setattr(settings_mod.QFileDialog, "getOpenFileName", lambda *a, **k: (str(f), ""))
    dlg = settings_mod.SettingsDialog(ConfigManager())
    dlg._browse_creds()
    assert not GOOGLE_CREDS.exists() and "Invalid" in dlg._google_status.text()


def test_sync_button_cancel_waits_for_the_worker(qapp):
    cancelled = []
    class Tray:
        _syncing = True
        def _cancel_sync(self): cancelled.append(1)
    dlg = settings_mod.SettingsDialog(ConfigManager(), tray_app=Tray())
    dlg._sync_btn.setText("Cancel Sync")
    dlg._on_sync_btn_clicked()
    assert cancelled == [1] and not dlg._sync_btn.isEnabled() and dlg._sync_btn.text() == "Cancelling…"
    dlg._restore_sync_btn("Sync cancelled")
    assert dlg._sync_btn.isEnabled() and dlg._sync_btn.text() == "Sync Now"


# ── Setup wizard ──────────────────────────────────────────────────────

def test_wizard_next_keeps_typed_lark_credentials(qapp):
    cfg = ConfigManager()
    w = wizard_mod.SetupWizard(cfg)
    w._lark_app_id.setText(" cli_abc "); w._lark_secret.setText("sec")
    w._step1_next()
    assert cfg.get("lark_app_id") == "cli_abc" and w._stack.currentIndex() == 1


def test_wizard_lark_authorize_flow(qapp):
    cfg = ConfigManager()
    w = wizard_mod.SetupWizard(cfg)
    w._authorize_lark()
    assert FakeWorker.instances == [] and "Enter App ID" in w._lark_status.text()

    w._lark_app_id.setText("cli_abc"); w._lark_secret.setText("sec")
    w._authorize_lark()
    worker = FakeWorker.instances[-1]
    assert worker.started and "Waiting" in w._lark_status.text()
    LARK_TOKEN.write_text("{}")
    worker.succeeded.emit()
    assert "Connected" in w._lark_status.text() and w._lark_auth_btn.isEnabled()


def test_wizard_shows_error_from_background_auth(qapp):
    w = wizard_mod.SetupWizard(ConfigManager())
    w._lark_app_id.setText("a"); w._lark_secret.setText("b")
    w._authorize_lark()
    FakeWorker.instances[-1].failed.emit("Lark OAuth error: redirect_uri mismatch")
    assert "redirect_uri" in w._lark_status.text() and w._lark_auth_btn.isEnabled()


def test_wizard_finish_warns_when_not_connected(qapp, monkeypatch):
    cfg = ConfigManager()
    w = wizard_mod.SetupWizard(cfg)
    monkeypatch.setattr(wizard_mod.QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    w._finish()
    assert w.result() != w.DialogCode.Accepted and cfg.is_first_run()

    monkeypatch.setattr(wizard_mod.QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w._finish()
    assert w.result() == w.DialogCode.Accepted and not cfg.is_first_run()
    assert cfg.get("schedule_anchor")


def test_wizard_finish_without_prompt_when_fully_configured(qapp, monkeypatch):
    cfg = ConfigManager()
    cfg.update({"lark_app_id": "a", "lark_app_secret": "b"})
    LARK_TOKEN.write_text("{}"); GOOGLE_CREDS.write_text("{}"); GOOGLE_TOKEN.write_text("{}")
    monkeypatch.setattr(wizard_mod.QMessageBox, "question",
                        lambda *a, **k: pytest.fail("should not ask when everything is connected"))
    w = wizard_mod.SetupWizard(cfg)
    w._finish()
    assert w.result() == w.DialogCode.Accepted


def test_wizard_accepts_legacy_pickle_token_as_connected(qapp):
    from sync.paths import LEGACY_GOOGLE_TOKEN
    GOOGLE_CREDS.write_text("{}"); LEGACY_GOOGLE_TOKEN.write_bytes(b"x")
    assert ConfigManager().is_google_configured()
    w = wizard_mod.SetupWizard(ConfigManager())
    assert "Connected" in w._google_status.text()


# ── OAuth worker threads ──────────────────────────────────────────────

def test_worker_reports_success_and_failure(qapp, monkeypatch):
    from sync import lark_auth
    results = []
    monkeypatch.setattr(lark_auth, "authorize", lambda cancel_event=None: {"ok": 1})
    w = oauth_worker.LarkAuthWorker()
    w.succeeded.connect(lambda: results.append("ok")); w.failed.connect(results.append)
    w.run()

    def boom(cancel_event=None): raise RuntimeError("denied")
    monkeypatch.setattr(lark_auth, "authorize", boom)
    w2 = oauth_worker.LarkAuthWorker()
    w2.succeeded.connect(lambda: results.append("ok")); w2.failed.connect(results.append)
    w2.run()
    assert results == ["ok", "denied"]


def test_worker_threads_deliver_signals_to_the_gui_thread(qapp, monkeypatch):
    from sync import lark_auth
    got = []
    monkeypatch.setattr(lark_auth, "authorize", lambda cancel_event=None: {})
    w = oauth_worker.LarkAuthWorker()
    w.succeeded.connect(lambda: got.append("ok"))
    w.start()
    w.wait(5000)
    for _ in range(20):
        qapp.processEvents()
    assert got == ["ok"]
    for _ in range(20):                                # finished -> reference released
        qapp.processEvents()
    assert w not in oauth_worker._ACTIVE
