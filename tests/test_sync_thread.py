from datetime import datetime

import pytest
from PyQt6.QtCore import QLockFile

import sync.google_client as google_client
import sync.lark_client as lark_client
import sync.sync_engine as sync_engine
from app.config_manager import ConfigManager, LOCK_FILE
from app.sync_thread import SyncThread
from sync.google_client import GoogleAuthRequired


class FakeEngine:
    result = {"folders": 1, "files_synced": 2, "files_skipped": 0, "errors": 0,
              "cancelled": False, "last_error": None}
    raises = None
    last_kwargs = None

    def __init__(self, **kw):
        FakeEngine.last_kwargs = kw

    def run(self):
        if FakeEngine.raises:
            raise FakeEngine.raises
        return dict(FakeEngine.result)


@pytest.fixture
def env(qapp, monkeypatch):
    FakeEngine.result = {"folders": 1, "files_synced": 2, "files_skipped": 0, "errors": 0,
                         "cancelled": False, "last_error": None}
    FakeEngine.raises = None
    FakeEngine.last_kwargs = None
    monkeypatch.setattr(sync_engine, "SyncEngine", FakeEngine)
    monkeypatch.setattr(lark_client, "LarkClient", lambda **kw: object())

    class FakeDrive:
        def __init__(self, **kw): pass
        def get_service(self): return object()
    monkeypatch.setattr(google_client, "GoogleDriveClient", FakeDrive)
    monkeypatch.setattr(SyncThread, "_send_lark_notification", lambda *a: None)

    cfg = ConfigManager()
    emitted = []
    thread = SyncThread(cfg)
    thread.completed.connect(emitted.append)
    return cfg, thread, emitted


def test_clean_sync_advances_both_markers(env):
    cfg, thread, emitted = env
    thread.run()
    assert len(emitted) == 1
    assert cfg.get("last_sync") and cfg.get("last_sync_clean") and cfg.get("fail_streak") == 0
    assert emitted[0]["fatal_error"] is None and emitted[0]["files_synced"] == 2


def test_sync_with_file_errors_does_not_advance_incremental_watermark(env):
    """Otherwise files that failed to sync would be skipped forever by incremental mode."""
    cfg, thread, emitted = env
    FakeEngine.result["errors"] = 3
    thread.run()
    assert cfg.get("last_sync") is not None
    assert cfg.get("last_sync_clean") is None


def test_crash_does_not_pretend_a_sync_happened(env):
    cfg, thread, emitted = env
    FakeEngine.raises = ConnectionError("offline")
    thread.run()
    assert len(emitted) == 1                          # one terminal event, not error + finished
    assert emitted[0]["fatal_error"] == "offline"
    assert cfg.get("last_sync") is None and cfg.get("last_sync_clean") is None
    assert cfg.get("fail_streak") == 1
    thread2 = SyncThread(cfg); thread2.completed.connect(emitted.append)
    thread2.run()
    assert cfg.get("fail_streak") == 2


def test_success_resets_failure_streak(env):
    cfg, thread, emitted = env
    cfg.set("fail_streak", 4)
    thread.run()
    assert cfg.get("fail_streak") == 0


def test_cancelled_sync_moves_no_marker(env):
    cfg, thread, emitted = env
    FakeEngine.result["cancelled"] = True
    thread.run()
    assert emitted[0]["cancelled"] is True
    assert cfg.get("last_sync") is None and cfg.get("last_sync_clean") is None


def test_incremental_watermark_comes_from_last_clean_sync(env):
    cfg, thread, _ = env
    cfg.update({"last_sync_clean": "2026-01-02T03:04:05", "last_sync": "2026-02-01T00:00:00"})
    thread.run()
    assert FakeEngine.last_kwargs["last_sync_ts"] == datetime.fromisoformat("2026-01-02T03:04:05").timestamp()


def test_watermark_falls_back_to_last_sync_for_v10_configs(env):
    cfg, thread, _ = env
    cfg.set("last_sync", "2026-02-01T00:00:00")
    thread.run()
    assert FakeEngine.last_kwargs["last_sync_ts"] == datetime.fromisoformat("2026-02-01T00:00:00").timestamp()


def test_conflict_and_limits_are_passed_to_the_engine(env):
    cfg, thread, _ = env
    cfg.update({"conflict": "skip", "max_file_mb": 7})
    thread.run()
    assert FakeEngine.last_kwargs["conflict"] == "skip" and FakeEngine.last_kwargs["max_file_mb"] == 7


def test_google_needs_reauth_is_reported_clearly(env, monkeypatch):
    cfg, thread, emitted = env
    class Expired:
        def __init__(self, **kw): pass
        def get_service(self): raise GoogleAuthRequired("Google authorization expired. Open Settings.")
    monkeypatch.setattr(google_client, "GoogleDriveClient", Expired)
    thread.run()
    assert "Google authorization expired" in emitted[0]["fatal_error"]
    assert cfg.get("last_sync") is None


def test_second_sync_is_refused_while_lock_is_held(env):
    cfg, thread, emitted = env
    held = QLockFile(str(LOCK_FILE))
    assert held.tryLock(0)
    try:
        thread.run()
    finally:
        held.unlock()
    assert emitted[0]["fatal_error"] == "Another sync is already running."


def test_lock_is_released_after_run(env):
    cfg, thread, _ = env
    thread.run()
    probe = QLockFile(str(LOCK_FILE))
    assert probe.tryLock(0)
    probe.unlock()


def test_sync_log_rotates_instead_of_growing_forever(env):
    from logging.handlers import RotatingFileHandler
    import logging
    cfg, thread, _ = env
    thread._setup_logging()
    assert any(isinstance(h, RotatingFileHandler) for h in logging.getLogger().handlers)
