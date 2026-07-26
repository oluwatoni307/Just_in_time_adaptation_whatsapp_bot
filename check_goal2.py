import asyncio
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import MessageLog
from app.channel import send_message
from app.webhook import on_incoming_message


async def main():
    # Criterion 1: sending creates a row with reply fields empty
    log_id = send_message(user_id=999, arm="cue", content="test")
    session = SessionLocal()
    row = session.query(MessageLog).filter(MessageLog.log_id == log_id).first()
    print("[1] row created with empty reply fields:", 
          row is not None and row.replied_at is None and row.reply_content is None)
    session.close()

    # Criterion 4: unsolicited message (no pending row) doesn't error
    on_incoming_message(user_id=12345, text="hello", timestamp=datetime.utcnow())
    print("[4] unsolicited message handled without error: True (see [webhook] log line above)")

    # Criteria 2, 3, 5: fire 10 sends, wait for delays to resolve, check reply rate
    print("\nFiring 10 sends, waiting up to 95s for replies to resolve...")
    log_ids = [send_message(user_id=999, arm="cue", content=f"batch {i}") for i in range(10)]

    await asyncio.sleep(95)  # covers the max 90s delay + buffer

    session = SessionLocal()
    replied = 0
    for lid in log_ids:
        row = session.query(MessageLog).filter(MessageLog.log_id == lid).first()
        if row.replied_at is not None:
            replied += 1
    session.close()

    print(f"[2/3/5] {replied}/10 sends got replies (expect roughly 7-9 out of 10)")


if __name__ == "__main__":
    asyncio.run(main())