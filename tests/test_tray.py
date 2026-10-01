import pytest
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QSystemTrayIcon

import app.tray_app as tray_mod
from app.config_manager import ConfigManager

Reason = QSystemTrayIcon.ActivationReason


class FakeThread:
    def __init__(self, running=True): self.running, self.cancelled = running, False
    def isRunning(self): return self.running
    def cancel(self): self.cancelled = True
    def wait(self, ms): return True


def make_tray(qapp, monkeypatch, mac):
    monkeypatch.setattr(tray_mod, "IS_MAC", mac)
    cfg = ConfigManager()
    cfg.set("schedule", "manual")                    # keep the scheduler out of the way
    tray = tray_mod.TrayApp(cfg, qapp)
    tray.messages = []
    monkeypatch.setattr(tray._tray, "showMessage", lambda title, body, *a: tray.messages.append((title, body)))
    return tray


@pytest.fixture
def win_tray(qapp, monkeypatch):
    return make_tray(qapp, monkeypatch, mac=False)


@pytest.fixture
def mac_tray(qapp, monkeypatch):
    return make_tray(qapp, monkeypatch, mac=True)


# ── Windows behaviour ─────────────────────────────────────────────────

def test_windows_right_click_menu_is_attached(win_tray):
    """v1.0.x set no context menu and ignored right-click, so the documented
    'right-click the tray icon' menu never appeared on Windows."""
    assert win_tray._tray.contextMenu() is win_tray._menu
    texts = [a.text() for a in win_tray._menu.actions()]
    assert "Sync Now" in texts and "Settings…" in texts and "Quit LarkSync" in texts
    assert "About LarkSync" in texts


@pytest.mark.parametrize("reason", [Reason.Trigger, Reason.DoubleClick])
def test_windows_left_click_opens_settings(win_tray, monkeypatch, reason):
    opened = []
    monkeypatch.setattr(win_tray, "_open_settings", lambda: opened.append(1))
    win_tray._on_tray_clicked(reason)
    assert opened == [1]


def test_windows_right_click_does_not_open_settings(win_tray, monkeypatch):
    opened = []
    monkeypatch.setattr(win_tray, "_open_settings", lambda: opened.append(1))
    win_tray._on_tray_clicked(Reason.Context)
    assert opened == []


def test_windows_icon_is_coloured_not_a_black_mask(win_tray):
    """Black-on-transparent is invisible on the (default) dark Windows taskbar."""
    img = win_tray._make_icon(idle=True).pixmap(32, 32).toImage()
    seen = {img.pixelColor(x, y).name() for x in range(32) for y in range(32)
            if img.pixelColor(x, y).alpha() > 200}
    assert seen and "#000000" not in seen
    assert not win_tray._make_icon(idle=True).isMask()


# ── macOS behaviour (kept as in v1.0.x) ───────────────────────────────

def test_mac_has_no_native_context_menu_and_toggles_on_click(mac_tray, monkeypatch):
    assert mac_tray._tray.contextMenu() is None
    shown = []
    monkeypatch.setattr(mac_tray._menu, "popup", lambda pos: shown.append(pos))
    monkeypatch.setattr(mac_tray._menu, "isVisible", lambda: False)
    mac_tray._on_tray_clicked(Reason.Trigger)
    assert len(shown) == 1


def test_mac_click_that_dismissed_the_menu_does_not_reopen_it(mac_tray, monkeypatch):
    shown = []
    monkeypatch.setattr(mac_tray._menu, "popup", lambda pos: shown.append(pos))
    mac_tray._on_menu_hidden()
    mac_tray._on_tray_clicked(Reason.Trigger)
    assert shown == []


def test_mac_icon_is_a_template_mask(mac_tray):
    assert mac_tray._make_icon().isMask()


def test_mac_menu_has_no_about_entry(mac_tray):
    assert "About LarkSync" not in [a.text() for a in mac_tray._menu.actions()]    # it lives in the native menu bar


# ── Sync state machine ────────────────────────────────────────────────

def test_cancel_keeps_busy_until_worker_really_ends(win_tray):
    win_tray._syncing, win_tray._thread = True, FakeThread()
    win_tray._cancel_sync()
    assert win_tray._thread.cancelled and win_tray._syncing is True
    assert win_tray._cancelling is True
    assert [a.text() for a in win_tray._menu.actions() if "Cancel" in a.text()] == ["⟳  Cancelling…"]
    win_tray._on_completed({"cancelled": True, "files_synced": 3, "errors": 0})
    assert win_tray._syncing is False and win_tray._cancelling is False
    assert "Cancelled" in win_tray.messages[-1][0]


def test_cannot_start_a_second_sync_over_a_running_thread(win_tray, monkeypatch):
    created = []
    monkeypatch.setattr(tray_mod, "SyncThread", lambda cfg: created.append(1))
    win_tray._thread = FakeThread(running=True)
    win_tray._start_sync()
    assert created == [] and win_tray._syncing is False


@pytest.mark.parametrize("stats,title", [
    ({"fatal_error": "offline"}, "Error"),
    ({"cancelled": True}, "Cancelled"),
    ({"files_synced": 4, "errors": 0, "duration_seconds": 5}, "Done"),
    ({"files_synced": 4, "errors": 2}, "Finished with errors"),
])
def test_completion_notifications(win_tray, stats, title):
    win_tray._syncing = True
    win_tray._on_completed(stats)
    assert len(win_tray.messages) == 1 and title in win_tray.messages[0][0]


def test_quit_cancels_running_sync(win_tray, monkeypatch):
    win_tray._thread = FakeThread()
    quit_called = []
    monkeypatch.setattr(win_tray.app, "quit", lambda: quit_called.append(1))
    win_tray._quit()
    assert win_tray._thread.cancelled and quit_called == [1]


# ── Scheduler wiring ──────────────────────────────────────────────────

def test_fresh_install_arms_schedule_but_does_not_sync(win_tray, monkeypatch):
    started = []
    monkeypatch.setattr(win_tray, "_start_sync", lambda: started.append(1))
    win_tray.config.update({"schedule": "weekly", "last_sync": None, "schedule_anchor": None})
    win_tray._check_schedule()
    assert started == [] and win_tray.config.get("schedule_anchor")


def test_overdue_schedule_catches_up(win_tray, monkeypatch):
    started = []
    monkeypatch.setattr(win_tray, "_start_sync", lambda: started.append(1))
    now = datetime.now()
    win_tray.config.update({
        "schedule": "daily", "schedule_hour": 0,
        "last_sync": (now - timedelta(days=3)).isoformat(),
        "schedule_anchor": (now - timedelta(days=10)).isoformat(),
    })
    win_tray._check_schedule()
    assert started == [1]


def test_corrupt_timestamps_do_not_crash_the_timer(win_tray):
    win_tray.config.update({"schedule": "weekly", "last_sync": "garbage", "schedule_day": "???"})
    win_tray._check_schedule()
    assert win_tray._last_sync_str() == "Unknown"
    assert win_tray._next_sync_str()


def test_menu_shows_next_sync_today_when_slot_is_still_ahead(win_tray, monkeypatch):
    now = datetime.now()
    hour = (now.hour + 1) % 24
    if hour == 0:
        pytest.skip("slot would fall on the next calendar day")
    win_tray.config.update({"schedule": "daily", "schedule_hour": hour, "schedule_minute": 0})
    assert win_tray._next_sync_str().endswith(f"{hour:02d}:00")
    assert datetime.now().strftime("%b %d") in win_tray._next_sync_str()
