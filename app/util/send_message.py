"""
send_message.py — orchestration layer. Resolves user_id -> phone_number
via repo, picks copy from library.py, hands off to messaging.py to send.
Implements the original sendMessage(userId, messageType) function.
"""

import random

from app.db.models import BanditArm
from app.db.repo import get_user
from app.util.messaging import send_whatsapp_text, SendResult
from app.util.library import MESSAGE_LIBRARY


def send_message(user_id: int, arm: BanditArm) -> SendResult:
    user = get_user(user_id)
    if user is None:
        return SendResult(failed=True, error=f"no user found for user_id={user_id}")

    phone_number = getattr(user, "phone_number", None)
    if not phone_number:
        return SendResult(failed=True, error=f"no phone_number for user_id={user_id}")

    text = random.choice(MESSAGE_LIBRARY.get(arm, ["Hey — checking in!"]))
    return send_whatsapp_text(phone_number, text)


def send_text(user_id: int, text: str) -> SendResult:
    """
    For free-form replies not part of the library — clarification prompts,
    fallback replies, the non-text acknowledgment.
    """
    user = get_user(user_id)
    if user is None:
        return SendResult(failed=True, error=f"no user found for user_id={user_id}")

    phone_number = getattr(user, "phone_number", None)
    if not phone_number:
        return SendResult(failed=True, error=f"no phone_number for user_id={user_id}")

    return send_whatsapp_text(phone_number, text)