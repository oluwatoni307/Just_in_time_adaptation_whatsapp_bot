import random
from datetime import datetime, time, timedelta

from .database import SessionLocal
from .models import BanditState, TimeBanditState


# Clock-time window each bucket actually covers. Used only for step 4 —
# once a bucket wins, pick an actual minute inside its real-world range.
BUCKET_WINDOWS = {
    "morning": (time(6, 0), time(10, 0)),
    "midday": (time(10, 0), time(14, 0)),
    "afternoon": (time(14, 0), time(17, 0)),
    "evening": (time(17, 0), time(21, 0)),
}


def select_time_bucket(user_id: int) -> str:
    session = SessionLocal()
    try:
        rows = (
            session.query(TimeBanditState)
            .filter(TimeBanditState.user_id == user_id)
            .all()
        )

        best_bucket = None
        best_sample = -1.0

        for row in rows:
            sample = random.betavariate(row.successes, row.failures)
            if sample > best_sample:
                best_sample = sample
                best_bucket = row.time_bucket

        return best_bucket
    finally:
        session.close()


def pick_send_time(bucket: str, reference_date=None) -> datetime:
    """Step 4: a random-but-locked minute inside the chosen bucket's
    actual clock-time window (e.g. afternoon = 2pm-5pm)."""
    reference_date = reference_date or datetime.utcnow().date()
    start, end = BUCKET_WINDOWS[bucket]

    start_dt = datetime.combine(reference_date, start)
    end_dt = datetime.combine(reference_date, end)

    total_seconds = int((end_dt - start_dt).total_seconds())
    offset = random.randint(0, total_seconds)

    return start_dt + timedelta(seconds=offset)


def _is_overdue(row: BanditState, now: datetime) -> bool:
    # min_interval_days == 0 means "no floor" — these arms (cue,
    # habit_pairing, log_prompt) always compete freely, never forced.
    if row.min_interval_days == 0:
        return False
    if row.last_sent_at is None:
        return True
    return (now - row.last_sent_at).days >= row.min_interval_days


def select_arm(user_id: int) -> str:
    """Public name matches the goal brief's spec exactly (`select_arm`).
    Internally, "arm" is still just the message-type column — see the
    translation note in resolution.py for why."""
    session = SessionLocal()
    try:
        rows = session.query(BanditState).filter(BanditState.user_id == user_id).all()
        now = datetime.utcnow()

        overdue = [row for row in rows if _is_overdue(row, now)]
        candidates = overdue if overdue else rows

        best_message_type = None
        best_sample = -1.0

        for row in candidates:
            sample = random.betavariate(row.successes, row.failures)
            if sample > best_sample:
                best_sample = sample
                best_message_type = row.arm

        return best_message_type
    finally:
        session.close()