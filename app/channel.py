# app/channel.py

import asyncio
import random
from datetime import datetime

from .database import SessionLocal
from .models import MessageLog


FAKE_REPLIES = [
    "ok",
    "done, just had some",
    "yep logged it",
    "sure",
    "will do",
]


def send_message(user_id: int, arm: str, content: str) -> int:
    session = SessionLocal()
    try:
        log = MessageLog(
            user_id=user_id,
            arm=arm,
            sent_at=datetime.utcnow(),
            replied_at=None,
            reply_content=None,
            counted_success=None,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        log_id = log.log_id
    finally:
        session.close()

    print(f"[mock channel] sent to user={user_id} arm={arm} content={content!r} log_id={log_id}")

    asyncio.create_task(_simulate_reply(user_id))

    return log_id


async def _simulate_reply(user_id: int):
    delay = random.uniform(10, 90)
    await asyncio.sleep(delay)

    if random.random() < 0.8:
        from .webhook import on_incoming_message
        fake_text = random.choice(FAKE_REPLIES)
        on_incoming_message(user_id, fake_text, datetime.utcnow())
    else:
        print(f"[mock channel] user={user_id} did not reply (simulated no-reply)")