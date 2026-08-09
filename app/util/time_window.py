"""
time_windows.py — single source of truth for TimeBucket -> fixed clock time.
Each bucket maps to one fixed hour, not a range. bandit.py and
evaluate_reply_outcome.py must both import from here, not define their own
copy — a mismatch would misassign or misscore messages.
"""

from datetime import datetime, time, timedelta
from typing import Optional

from app.db.models import TimeBucket

# PLACEHOLDER — confirm these against your real send schedule
TIME_BUCKET_TIMES = {
    TimeBucket.morning: time(8, 0),
    TimeBucket.midday: time(12, 0),
    TimeBucket.afternoon: time(16, 0),
    TimeBucket.evening: time(20, 0),
}


def round_to_nearest_hour(dt: datetime) -> datetime:
    if dt.minute >= 30:
        dt = dt + timedelta(hours=1)
    return dt.replace(minute=0, second=0, microsecond=0)


from zoneinfo import ZoneInfo

NIGERIA_TZ = ZoneInfo("Africa/Lagos")

def current_bucket(now: Optional[datetime] = None) -> Optional[TimeBucket]:
    if now is None:
        now = datetime.now(NIGERIA_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=NIGERIA_TZ)
    else:
        now = now.astimezone(NIGERIA_TZ)

    rounded = round_to_nearest_hour(now).time()

    for bucket, fixed_time in TIME_BUCKET_TIMES.items():
        if rounded == fixed_time:
            return bucket
    return None