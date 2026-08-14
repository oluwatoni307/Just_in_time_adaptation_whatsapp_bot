"""
Daily cron job: run_bandit_for_users

Runs every day at 6am. For each user, first updates their
consecutive_quiet_days based on whether they replied yesterday, then
picks how many messages to send today, then for each message picks a
time slot and message type via bandits, and saves the plan to the
database.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict

from app.util.engagement import get_engagement_level as get_daily_message_cap, CAPS_BY_LEVEL
from app.bandit import select_time_bucket as time_slot_bandit, select_arm as message_type_bandit
from app.db.repo import (
    SaveResult,
    get_all_users,
    save_today_data,
    user_replied_since,
    update_consecutive_quiet_days,
)

logger = logging.getLogger("bandit_scheduler")

from typing import TypedDict

class BanditData(TypedDict):
    time_bucket: str
    arm: str

def run_bandit_for_users():
    users = get_all_users()  # disk read
    yesterday = datetime.utcnow() - timedelta(days=1)

    for user in users:
        # update quiet-days counter first, cap logic below depends on it
        replied = user_replied_since(user.user_id, yesterday)
        new_quiet_days = 0 if replied else user.consecutive_quiet_days + 1
        update_result = update_consecutive_quiet_days(user.user_id, new_quiet_days)
        if getattr(update_result, "failed", False):
            logger.error("Failed to update consecutive_quiet_days for user_id=%s: %s",
                         user.user_id, update_result.error)
        user.consecutive_quiet_days = new_quiet_days  # keep in-memory copy fresh

        daily_message_cap = CAPS_BY_LEVEL.get(get_daily_message_cap(user), 0)
        if daily_message_cap <= 0:
            continue  # nothing to schedule

        # bandit_data: Dict[timeslot, message_type] for this user today
        bandit_data: Dict[str, str] = {}
        used_time_slots = set()

        for _ in range(daily_message_cap):
            time_slot = time_slot_bandit(user.user_id)

            if time_slot in used_time_slots:
                continue  # already scheduled this slot — skip, no fallback

            message_type = message_type_bandit(user.user_id)
            used_time_slots.add(time_slot)
            bandit_data[time_slot] = message_type

        result = save_today_data(user.user_id, bandit_data)  # disk write
        if getattr(result, "failed", False):
            logger.error(
                "Failed to save bandit data for user_id=%s: %s",
                user.user_id, getattr(result, "error", "unknown error"),
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bandit_for_users()