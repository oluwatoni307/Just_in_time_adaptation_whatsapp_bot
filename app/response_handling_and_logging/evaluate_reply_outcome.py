"""
handleIncomingMessage — called whenever a user sends a message in.

Text messages: mark the latest open MessageLog row as replied (regardless
of whether the LLM call itself succeeds), then route on intent.
Non-text messages: canned reply, no reply-tracking (nothing to mark).
"""

import logging

from app.db.repo import get_latest_unreplied_message, mark_replied
from llm import process as llm_process          # ASSUMED interface — not yet verified
from app.util.messaging import send_message              # ASSUMED interface — not yet verified

logger = logging.getLogger("handle_incoming_message")

TEXT = "text"
LOG_WATER_INTAKE = "log_water_intake"
CLARIFY_STATUS = "clarify_status"


def build_fallback_reply() -> str:
    return "Not sure I caught that — can you rephrase?"


def handle_incoming_message(message):
    if message.type != TEXT:
        send_message(message.userId, "Got it — text works best for now.")
        return

    open_message = get_latest_unreplied_message(message.userId)
    if open_message is not None:
        result = mark_replied(open_message.log_id, message.text)
        if getattr(result, "failed", False):
            logger.error("Failed to mark replied for user_id=%s: %s",
                         message.userId, result.error)
    # else: unsolicited message, nothing open to mark — proceed anyway

    response = llm_process(message.text)
    if getattr(response, "failed", False):
        logger.error("LLM processing failed for user_id=%s", message.userId)
        return

    if response.intent == LOG_WATER_INTAKE:
        log_intake(message.userId, response.amount)
    elif response.intent == CLARIFY_STATUS:
        send_message(message.userId, "Can you clarify — are you asking about your current hydration status?")
    else:
        send_message(message.userId, build_fallback_reply())