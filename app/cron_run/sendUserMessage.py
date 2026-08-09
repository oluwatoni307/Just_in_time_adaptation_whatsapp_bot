"""
Cron job: sendUserMessage
...
"""

import logging
import sys

from app.db.models import TimeBucket
from app.db.repo import get_scheduled_for_bucket, log_message_sent
from app.util.time_window import current_bucket
from app.util.send_message import send_message

logger = logging.getLogger("send_user_message")


def send_user_message(time_bucket=None):
    time_bucket = time_bucket or current_bucket()
    if not time_bucket:
        logger.warning("No current time bucket found.")
        return

    rows = get_scheduled_for_bucket(time_bucket)

    for row in rows:
        result = send_message(row.user_id, row.arm)
        if getattr(result, "failed", False):
            logger.error("Failed to send message for user_id=%s: %s",
                         row.user_id, getattr(result, "error", "unknown error"))
            continue

        log_result = log_message_sent(row.user_id, row.arm)
        if getattr(log_result, "failed", False):
            logger.error("Failed to log sent message for user_id=%s: %s",
                         row.user_id, log_result.error)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bucket_arg = sys.argv[1] if len(sys.argv) > 1 else None
    forced_bucket = TimeBucket[bucket_arg] if bucket_arg else None
    send_user_message(forced_bucket)