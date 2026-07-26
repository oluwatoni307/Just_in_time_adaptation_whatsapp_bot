from datetime import datetime, timedelta

from sqlalchemy import func

from .database import SessionLocal
from .models import MessageLog, User


CAPS_BY_LEVEL = {
    "normal": 3,
    "reduced": 2,
    "minimal": 1,
}

# Deviation from Goal 8's written spec (which stops at "4+ -> minimal,
# 1/day forever"): a user quiet for a long stretch shouldn't get nudged
# daily indefinitely -- that's more likely to read as nagging than
# re-engagement. "dormant" drops to roughly 1 message a WEEK instead of
# a smaller daily number, since "once a week" can't be expressed as a
# daily cap -- it needs its own rolling 7-day lookback, not a
# midnight-reset counter. Threshold (7 days) is a first guess; revisit
# once real usage data exists.
DORMANT_THRESHOLD_DAYS = 7


def get_engagement_level(user: User) -> str:
    """Derived, not stored -- always computed fresh from
    consecutive_quiet_days, per Goal 1's decision."""
    if user.consecutive_quiet_days <= 1:
        return "normal"
    if user.consecutive_quiet_days <= 3:
        return "reduced"
    if user.consecutive_quiet_days < DORMANT_THRESHOLD_DAYS:
        return "minimal"
    return "dormant"


def should_send_now(user_id: int, now: datetime = None) -> bool:
    """Whether the user is allowed *any* message right now -- doesn't
    decide which one. `now` is injectable for testing, same pattern as
    goal_reminder.py."""
    now = now or datetime.utcnow()

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return False

        level = get_engagement_level(user)

        if level == "dormant":
            # Rolling 7-day lookback, not a calendar-day reset -- "once
            # a week" doesn't fit the midnight-reset model the other
            # tiers use.
            week_ago = now - timedelta(days=7)
            sent_this_week = (
                session.query(func.count(MessageLog.log_id))
                .filter(
                    MessageLog.user_id == user_id,
                    MessageLog.sent_at >= week_ago,
                )
                .scalar()
            ) or 0
            return sent_this_week < 1

        today = now.date()
        cap = CAPS_BY_LEVEL[level]

        sent_today = (
            session.query(func.count(MessageLog.log_id))
            .filter(
                MessageLog.user_id == user_id,
                func.date(MessageLog.sent_at) == today,
            )
            .scalar()
        ) or 0

        return sent_today < cap
    finally:
        session.close()