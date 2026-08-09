"""
send_message.py — orchestration layer. user_id IS the phone number (see
the phone-number-as-primary-key migration), so no separate lookup needed
to get a sendable number — just confirm the user exists.
Implements the original sendMessage(userId, messageType) function.
"""

import random

from app.db.models import BanditArm
from app.db.repo import get_user
from app.util.library import MESSAGE_LIBRARY


def _to_e164(local_number: str) -> str:
    """
    Our db stores local format ('08142156076'). WhatsApp's API needs
    E.164 digits, no '+' ('2348142156076'). Reverse of main.py's
    _normalize_phone.
    TODO: same flag as before — storing E.164 everywhere would remove
    the need for conversion on both ends.
    """
    if local_number.startswith("0"):
        return "234" + local_number[1:]
    return local_number


from app.util.messaging import send_whatsapp_text, send_whatsapp_template, SendResult

def send_message(user_id: int, arm: BanditArm) -> SendResult:
    user = get_user(user_id)
    if user is None:
        return SendResult(failed=True, error=f"no user found for user_id={user_id}")

    messages = MESSAGE_LIBRARY.get(arm)
    if not messages:
        return SendResult(failed=True, error=f"no messages found for arm={arm}")

    index = random.randrange(len(messages))
    template_name = f"hydration_{arm.value}_{index + 1}"

    return send_whatsapp_template(_to_e164(user.user_id), template_name)


def send_text(user_id: int, text: str) -> SendResult:
    """
    For free-form replies not part of the library — clarification prompts,
    fallback replies, the non-text acknowledgment.
    """
    user = get_user(user_id)
    if user is None:
        return SendResult(failed=True, error=f"no user found for user_id={user_id}")

    return send_whatsapp_text(_to_e164(user.user_id), text)