from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.db.database import SessionLocal
from app.db.models import User, DailySchedule, BanditArm, TimeBucket, BanditState, TimeBanditState, MessageLog


@dataclass
class SaveResult:
    failed: bool
    error: str = ""


@dataclass
class ScheduledMessage:
    user_id: int
    arm: BanditArm


def get_all_users() -> List[User]:
    db = SessionLocal()
    try:
        return db.query(User).all()
    finally:
        db.close()


def create_user(phone_number: str) -> User:
    """
    Adds a new user keyed by phone_number (our identity link, not Firestore's
    firebase_uid — that gets filled in later via set_firebase_uid once the
    account is linked). Seeds bandit state in the same call.
    """
    db = SessionLocal()
    try:
        user = User(
            user_id=phone_number,
            firebase_uid=None,
            onboarded_at=datetime.now(),
            consecutive_quiet_days=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    finally:
        db.close()

    seed_bandit_state(phone_number)
    return user


def seed_bandit_state(user_id: int) -> SaveResult:
    """
    Call once, at user onboarding. Inserts one BanditState row per BanditArm
    and one TimeBanditState row per TimeBucket, using the model's own
    successes=1/failures=1 defaults. Without this, a new user has no rows
    for select_time_bucket / select_arm to choose from.
    """
    db = SessionLocal()
    try:
        for arm in BanditArm:
            db.add(BanditState(user_id=user_id, arm=arm))
        for bucket in TimeBucket:
            db.add(TimeBanditState(user_id=user_id, time_bucket=bucket))
        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()


def save_today_data(user_id: int, schedule: Dict[TimeBucket, BanditArm]) -> SaveResult:
    """
    Overwrite today's schedule for this user: delete existing rows,
    insert the new (time_bucket, arm) pairs. No date column, so this
    IS the overwrite — call it once per user per day.
    """
    db = SessionLocal()
    try:
        db.query(DailySchedule).filter(DailySchedule.user_id == user_id).delete()
        for time_bucket, arm in schedule.items():
            db.add(DailySchedule(user_id=user_id, time_bucket=time_bucket, arm=arm))
        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()


def get_scheduled_for_bucket(time_bucket: TimeBucket) -> List[ScheduledMessage]:
    """
    Reads DailySchedule directly for everyone scheduled at this time_bucket.
    """
    db = SessionLocal()
    try:
        rows = db.query(DailySchedule).filter(
            DailySchedule.time_bucket == time_bucket
        ).all()
        return [ScheduledMessage(user_id=r.user_id, arm=r.arm) for r in rows]
    finally:
        db.close()


def log_message_sent(user_id: int, arm: BanditArm) -> SaveResult:
    """
    Writes a MessageLog row right after a message is sent.
    replied_at / counted_success start null — evaluateReplyOutcomes fills
    those in later.
    """
    db = SessionLocal()
    try:
        db.add(MessageLog(
            user_id=user_id,
            arm=arm,
            sent_at=datetime.utcnow(),
        ))
        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()


def get_latest_unreplied_message(user_id: int):
    """
    Most recent MessageLog row for this user with replied_at still null.
    Returns None if there's nothing open (e.g. unsolicited text).
    """
    db = SessionLocal()
    try:
        return db.query(MessageLog).filter(
            MessageLog.user_id == user_id,
            MessageLog.replied_at.is_(None)
        ).order_by(MessageLog.sent_at.desc()).first()
    finally:
        db.close()


def mark_replied(log_id: int, reply_content: str) -> SaveResult:
    db = SessionLocal()
    try:
        row = db.query(MessageLog).filter(MessageLog.log_id == log_id).first()
        if row is None:
            return SaveResult(failed=True, error=f"no MessageLog row for log_id={log_id}")
        row.replied_at = datetime.utcnow()
        row.reply_content = reply_content
        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()


def get_unevaluated_messages_for_bucket(time_bucket: TimeBucket, window_start, window_end):
    """
    MessageLog rows not yet scored, sent within [window_start, window_end)
    today. window_start/window_end are datetimes — caller computes them
    from TIME_BUCKET_WINDOWS (see evaluateReplyOutcomesScript.py).
    """
    db = SessionLocal()
    try:
        return db.query(MessageLog).filter(
            MessageLog.counted_success.is_(None),
            MessageLog.sent_at >= window_start,
            MessageLog.sent_at < window_end,
        ).all()
    finally:
        db.close()


def record_bandit_outcome(user_id: int, arm: BanditArm, time_bucket: TimeBucket, success: bool) -> SaveResult:
    """
    Increments successes or failures by 1 on both BanditState (per arm)
    and TimeBanditState (per time_bucket) for this user.
    """
    db = SessionLocal()
    try:
        bandit_row = db.query(BanditState).filter(
            BanditState.user_id == user_id, BanditState.arm == arm
        ).first()
        time_row = db.query(TimeBanditState).filter(
            TimeBanditState.user_id == user_id, TimeBanditState.time_bucket == time_bucket
        ).first()
        if bandit_row is None or time_row is None:
            return SaveResult(failed=True, error=f"missing bandit state row for user_id={user_id}")

        if success:
            bandit_row.successes += 1
            time_row.successes += 1
        else:
            bandit_row.failures += 1
            time_row.failures += 1

        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()


def mark_message_evaluated(log_id: int, success: bool) -> SaveResult:
    db = SessionLocal()
    try:
        row = db.query(MessageLog).filter(MessageLog.log_id == log_id).first()
        if row is None:
            return SaveResult(failed=True, error=f"no MessageLog row for log_id={log_id}")
        row.counted_success = success
        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()


def get_user(user_id: int) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.user_id == user_id).first()
    finally:
        db.close()


def get_user_by_phone(phone_number: str) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.user_id == phone_number).first()
    finally:
        db.close()


def set_firebase_uid(phone_number: str, firebase_uid: str) -> SaveResult:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == phone_number).first()
        if user is None:
            return SaveResult(failed=True, error=f"no user for phone_number={phone_number}")
        user.firebase_uid = firebase_uid
        db.commit()
        return SaveResult(failed=False)
    except Exception as e:
        db.rollback()
        return SaveResult(failed=True, error=str(e))
    finally:
        db.close()