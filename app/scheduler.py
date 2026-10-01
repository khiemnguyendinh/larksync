"""
Schedule maths (pure functions — no Qt, easy to unit-test).

The old scheduler only fired if the machine happened to be awake in the
scheduled hour of the scheduled weekday, so a laptop that was asleep (or a
Windows PC that was off) at 08:00 Monday silently skipped the whole week.

New rule: find the most recent scheduled moment `due` (<= now). A sync is
needed when the last completed sync happened before `due`. That catches up
automatically after sleep / shutdown, and a manual sync made after `due`
satisfies the schedule.
"""

from datetime import datetime, timedelta
from typing import Optional

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

RETRY_BASE   = timedelta(minutes=15)    # wait after the first failed attempt
RETRY_CAP    = timedelta(hours=4)
MAX_RETRIES  = 6                        # then wait for the next scheduled period


def _clean_hm(hour, minute):
    try:
        hour = min(max(int(hour), 0), 23)
    except (TypeError, ValueError):
        hour = 8
    try:
        minute = min(max(int(minute), 0), 59)
    except (TypeError, ValueError):
        minute = 0
    return hour, minute


def last_due(now: datetime, schedule: str, day: str = "Monday",
             hour=8, minute=0) -> Optional[datetime]:
    """Most recent scheduled moment that is <= now, or None for manual mode."""
    hour, minute = _clean_hm(hour, minute)
    if schedule == "daily":
        t = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return t - timedelta(days=1) if t > now else t
    if schedule == "weekly":
        dow = DAY_NAMES.index(day) if day in DAY_NAMES else 0
        back = (now.weekday() - dow) % 7
        t = (now - timedelta(days=back)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return t - timedelta(days=7) if t > now else t
    return None


def next_due(now: datetime, schedule: str, day: str = "Monday",
             hour=8, minute=0) -> Optional[datetime]:
    """First scheduled moment strictly after now, or None for manual mode."""
    ld = last_due(now, schedule, day, hour, minute)
    if ld is None:
        return None
    return ld + (timedelta(days=1) if schedule == "daily" else timedelta(days=7))


def parse_iso(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def should_run(now: datetime, schedule: str, day: str, hour, minute,
               last_sync: Optional[datetime],
               anchor: Optional[datetime] = None,
               last_attempt: Optional[datetime] = None,
               fail_streak: int = 0) -> bool:
    """
    Decide whether a scheduled sync must start now.

    last_sync     last sync that actually ran to the end (manual or scheduled)
    anchor        when the schedule was armed (first launch, or the schedule was
                  changed in Settings) so a new install never fires a surprise sync
    last_attempt  last attempt of any kind; fail_streak counts consecutive attempts
                  that failed before syncing anything (offline, expired token…).
                  Those are retried with back-off instead of waiting a week.
    """
    due = last_due(now, schedule, day, hour, minute)
    if due is None:
        return False

    # The later of "last sync" and "schedule armed": changing the schedule in
    # Settings re-arms it, so an overdue slot is not fired the moment you save.
    baseline = max((t for t in (last_sync, anchor) if t is not None), default=None)
    if baseline is None or baseline >= due:
        return False

    if fail_streak > 0 and last_attempt is not None and last_attempt >= due:
        if fail_streak >= MAX_RETRIES:
            return False
        wait = min(RETRY_BASE * (2 ** (fail_streak - 1)), RETRY_CAP)
        return now - last_attempt >= wait
    return True
