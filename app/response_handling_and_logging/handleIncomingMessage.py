"""
handleIncomingMessage — called whenever a user sends a message in.

Text messages: mark the latest open MessageLog row as replied, ensure the
user exists in our db (onboard if not), then hand off to the agent
(llm.process) which handles logging/clarifying/replying itself, and send
back whatever it says.

Non-text messages: canned reply, no reply-tracking (nothing to mark).
"""

import logging

from app.db.repo import get_latest_unreplied_message, mark_replied, get_user_by_phone, create_user
from app.response_handling_and_logging.llm import process as llm_process
from app.util.send_message import send_text

logger = logging.getLogger("handle_incoming_message")

TEXT = "text"


def handle_incoming_message(message):
    phone_number = message.userId

    if message.type != TEXT:
        send_text(phone_number, "Got it — text works best for now.")
        return

    # onboard brand-new numbers before anything else touches them
    user = get_user_by_phone(phone_number)
    if user is None:
        create_user(phone_number)

    open_message = get_latest_unreplied_message(phone_number)
    if open_message is not None:
        result = mark_replied(open_message.log_id, message.text)
        if getattr(result, "failed", False):
            logger.error("Failed to mark replied for user_id=%s: %s",
                         phone_number, result.error)
    # else: unsolicited message, nothing open to mark — proceed anyway

    result = llm_process(phone_number, message.text)
    if result.failed:
        logger.error("LLM processing failed for user_id=%s: %s", phone_number, result.error)
        send_text(phone_number, "Something went wrong on my end — try again in a bit?")
        return

    send_text(phone_number, result.reply_text)