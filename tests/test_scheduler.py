from datetime import datetime, timedelta

from app.scheduler import last_due, next_due, should_run

# 2026-10-07 is a Wednesday
WED_NOON = datetime(2026, 10, 7, 12, 0)


def test_weekly_last_due_is_most_recent_slot():
    assert last_due(WED_NOON, "weekly", "Monday", 8) == datetime(2026, 10, 5, 8, 0)
    # today is the target day but the hour has not come yet -> previous week
    assert last_due(datetime(2026, 10, 5, 7, 59), "weekly", "Monday", 8) == datetime(2026, 9, 28, 8, 0)
    assert last_due(datetime(2026, 10, 5, 8, 0), "weekly", "Monday", 8) == datetime(2026, 10, 5, 8, 0)


def test_next_due_today_when_hour_not_passed():
    # v1.0.x showed *next week* when the slot was still ahead today
    now = datetime(2026, 10, 5, 7, 0)  # Monday 07:00
    assert next_due(now, "weekly", "Monday", 8) == datetime(2026, 10, 5, 8, 0)
    assert next_due(now, "daily", "Monday", 8) == datetime(2026, 10, 5, 8, 0)


def test_daily_and_manual():
    assert last_due(datetime(2026, 10, 7, 7, 0), "daily", "Monday", 8) == datetime(2026, 10, 6, 8, 0)
    assert last_due(WED_NOON, "manual") is None
    assert next_due(WED_NOON, "manual") is None


def test_invalid_values_do_not_crash():
    assert last_due(WED_NOON, "weekly", "Funday", "x", None) == datetime(2026, 10, 5, 8, 0)


def test_catch_up_after_missed_slot():
    # Machine was off at Monday 08:00; it is Wednesday and the last sync was a week earlier.
    assert should_run(WED_NOON, "weekly", "Monday", 8, 0, last_sync=datetime(2026, 9, 28, 8, 5)) is True


def test_no_run_when_already_synced_since_slot():
    assert should_run(WED_NOON, "weekly", "Monday", 8, 0, last_sync=datetime(2026, 10, 6, 9, 0)) is False


def test_manual_sync_after_slot_satisfies_schedule():
    assert should_run(datetime(2026, 10, 5, 9, 0), "weekly", "Monday", 8, 0,
                      last_sync=datetime(2026, 10, 5, 8, 30)) is False


def test_new_install_waits_for_first_slot():
    anchor = datetime(2026, 10, 7, 11, 0)                      # armed Wed 11:00
    assert should_run(WED_NOON, "weekly", "Monday", 8, 0, last_sync=None, anchor=anchor) is False
    nxt = datetime(2026, 10, 12, 8, 1)                         # following Monday
    assert should_run(nxt, "weekly", "Monday", 8, 0, last_sync=None, anchor=anchor) is True


def test_changing_schedule_rearms_instead_of_firing_immediately():
    old_sync = datetime(2026, 8, 1, 8, 0)                      # months ago, schedule was "manual"
    just_saved = datetime(2026, 10, 7, 11, 59)
    assert should_run(WED_NOON, "daily", "Monday", 8, 0, last_sync=old_sync, anchor=just_saved) is False


def test_manual_mode_never_runs():
    assert should_run(WED_NOON, "manual", "Monday", 8, 0, last_sync=None, anchor=datetime(2020, 1, 1)) is False


def test_failed_attempt_retries_with_backoff():
    last_sync = datetime(2026, 9, 28, 8, 5)
    failed_at = datetime(2026, 10, 5, 8, 1)                    # offline right after wake
    args = ("weekly", "Monday", 8, 0)
    assert should_run(failed_at + timedelta(minutes=5), *args, last_sync=last_sync,
                      last_attempt=failed_at, fail_streak=1) is False
    assert should_run(failed_at + timedelta(minutes=16), *args, last_sync=last_sync,
                      last_attempt=failed_at, fail_streak=1) is True
    # second failure doubles the wait
    assert should_run(failed_at + timedelta(minutes=20), *args, last_sync=last_sync,
                      last_attempt=failed_at, fail_streak=2) is False
    assert should_run(failed_at + timedelta(minutes=31), *args, last_sync=last_sync,
                      last_attempt=failed_at, fail_streak=2) is True


def test_gives_up_after_max_retries_until_next_slot():
    last_sync = datetime(2026, 9, 28, 8, 5)
    attempt = datetime(2026, 10, 5, 9, 0)
    assert should_run(datetime(2026, 10, 6, 9, 0), "weekly", "Monday", 8, 0, last_sync=last_sync,
                      last_attempt=attempt, fail_streak=6) is False
    # a new slot resets the situation (attempt predates the new due time)
    assert should_run(datetime(2026, 10, 12, 8, 1), "weekly", "Monday", 8, 0, last_sync=last_sync,
                      last_attempt=attempt, fail_streak=6) is True
