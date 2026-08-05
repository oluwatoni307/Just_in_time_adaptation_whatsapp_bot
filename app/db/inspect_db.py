"""
Read-only inspection script — one function per table, plus print_all().

Run all:       python -m app.db.inspect_db
Run one table: python -m app.db.inspect_db users
               python -m app.db.inspect_db daily_schedule
"""

import sys

from app.db.database import SessionLocal
from app.db.models import User, BanditState, TimeBanditState, DailySchedule, MessageLog


def print_table(title, rows, columns):
    print(f"\n=== {title} ===")
    if not rows:
        print("  (empty)")
        return

    data = [[str(getattr(r, col)) for col in columns] for r in rows]
    widths = [max(len(col), *(len(row[i]) for row in data)) for i, col in enumerate(columns)]

    header = "  ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    print("  " + header)
    print("  " + "-" * len(header))
    for row in data:
        print("  " + "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))


def print_users():
    db = SessionLocal()
    try:
        print_table("users", db.query(User).all(),
                     ["user_id", "firebase_uid", "onboarded_at", "consecutive_quiet_days"])
    finally:
        db.close()


def print_bandit_state():
    db = SessionLocal()
    try:
        print_table("bandit_state", db.query(BanditState).all(),
                     ["user_id", "arm", "successes", "failures"])
    finally:
        db.close()


def print_time_bandit_state():
    db = SessionLocal()
    try:
        print_table("time_bandit_state", db.query(TimeBanditState).all(),
                     ["user_id", "time_bucket", "successes", "failures"])
    finally:
        db.close()


def print_daily_schedule():
    db = SessionLocal()
    try:
        print_table("daily_schedule", db.query(DailySchedule).all(),
                     ["user_id", "time_bucket", "arm"])
    finally:
        db.close()


def print_message_log():
    db = SessionLocal()
    try:
        print_table("message_log", db.query(MessageLog).all(),
                     ["log_id", "user_id", "arm", "sent_at", "replied_at", "counted_success"])
    finally:
        db.close()


TABLE_PRINTERS = {
    "users": print_users,
    "bandit_state": print_bandit_state,
    "time_bandit_state": print_time_bandit_state,
    "daily_schedule": print_daily_schedule,
    "message_log": print_message_log,
}


def print_all():
    for printer in TABLE_PRINTERS.values():
        printer()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        print_all()
    elif arg in TABLE_PRINTERS:
        TABLE_PRINTERS[arg]()
    else:
        print(f"Unknown table '{arg}'. Options: {', '.join(TABLE_PRINTERS)}")