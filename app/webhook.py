from datetime import datetime

from .database import SessionLocal
from .models import MessageLog


def on_incoming_message(user_id: int, text: str, timestamp: datetime):
    session = SessionLocal()
    try:
        pending = (
            session.query(MessageLog)
            .filter(MessageLog.user_id == user_id)
            .filter(MessageLog.replied_at.is_(None))
            .order_by(MessageLog.sent_at.desc())
            .first()
        )

        if pending is not None:
            pending.replied_at = timestamp
            pending.reply_content = text
            session.commit()
            print(f"[webhook] matched reply for user={user_id} log_id={pending.log_id}: {text!r}")
        else:
            print(f"[webhook] unsolicited message from user={user_id}: {text!r} (no pending message_log row)")
    finally:
        session.close()