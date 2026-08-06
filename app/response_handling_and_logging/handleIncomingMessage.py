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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("handle_incoming_message")

TEXT = "text"


def handle_incoming_message(message):
    phone_number = message.userId
    logger.info("STEP 1/6 received: phone_number=%r type=%r text=%r",
                phone_number, message.type, message.text)

    if message.type != TEXT:
        result = send_text(phone_number, "Got it — text works best for now.")
        logger.info("STEP non-text reply sent: failed=%s error=%r",
                     getattr(result, "failed", None), getattr(result, "error", None))
        return

    # onboard brand-new numbers before anything else touches them
    user = get_user_by_phone(phone_number)
    logger.info("STEP 2/6 get_user_by_phone: found=%s", user is not None)

    if user is None:
        user = create_user(phone_number)
        logger.info("STEP 2b/6 create_user: user_id=%r firebase_uid=%r",
                     getattr(user, "user_id", None), getattr(user, "firebase_uid", None))

    open_message = get_latest_unreplied_message(phone_number)
    logger.info("STEP 3/6 get_latest_unreplied_message: found=%s", open_message is not None)

    if open_message is not None:
        result = mark_replied(open_message.log_id, message.text)
        logger.info("STEP 3b/6 mark_replied: failed=%s error=%r",
                     getattr(result, "failed", None), getattr(result, "error", None))
        if getattr(result, "failed", False):
            logger.error("Failed to mark replied for user_id=%s: %s",
                         phone_number, result.error)
    # else: unsolicited message, nothing open to mark — proceed anyway

    logger.info("STEP 4/6 calling llm_process...")
    result = llm_process(phone_number, message.text)
    logger.info("STEP 5/6 llm_process returned: failed=%s error=%r reply_text=%r",
                result.failed, getattr(result, "error", None), getattr(result, "reply_text", None))

    if result.failed:
        logger.error("LLM processing failed for user_id=%s: %s", phone_number, result.error)
        send_result = send_text(phone_number, "Something went wrong on my end — try again in a bit?")
        logger.info("STEP 5b/6 fallback send_text: failed=%s error=%r",
                     getattr(send_result, "failed", None), getattr(send_result, "error", None))
        return

    logger.info("STEP 6/6 calling send_text with reply_text=%r", result.reply_text)
    send_result = send_text(phone_number, result.reply_text)
    logger.info("STEP 6/6 send_text returned: failed=%s error=%r",
                getattr(send_result, "failed", None), getattr(send_result, "error", None))