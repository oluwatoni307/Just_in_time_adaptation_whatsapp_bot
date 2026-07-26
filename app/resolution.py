"""
resolution.py — turning "sent, still waiting" into a real outcome.

Goal 2 proved a message can sit in `message_log` with `replied_at IS NULL`
for a while, unresolved, mid-flight. This file is where that limbo ends.
Every unresolved row here gets exactly one of three fates:

  1. SUCCESS  — a reply landed, at any point. The user engaged.
  2. RETRY    — no reply yet, but we haven't nudged a second time.
                One gentle follow-up, then we wait again.
  3. FAILURE  — no reply even after the follow-up. We stop pretending
                and record it as a miss.

Think of RETRY as a second knock on the door, not a longer deadline.
The reason it's its own state (`retry_sent`) rather than a doubled
timer is that the follow-up is a real, visible event to the user —
something they can react to — not an invisible extension of a clock
they never saw ticking. Silence for 4 hours straight and silence
followed by a nudge at hour 2 are different user experiences, even
though the total wait is identical.

Carried-over design decision (from the Goal 2 flag): a reply always
resolves to the *most recent* pending message for that user, no
content parsing. If that ever proves wrong in practice, revisit —
not here, not speculatively.
"""

from datetime import datetime, timedelta

from .channel import send_message
from .database import SessionLocal
from .models import BanditState, MessageLog, User

# Schema note: the database column is called `arm` (borrowed from the
# multi-armed-bandit algorithm this table feeds). Read it as "message
# type" everywhere below — cue, habit_pairing, log_prompt, etc. are
# each one arm/type. The column name isn't changing; this comment is
# just the translation key.

# Two hours, per spec. Named once so "why 2?" has a single home,
# instead of the literal number 2 showing up unexplained three times
# further down.
RESPONSE_WINDOW = timedelta(hours=2)

# These three message types are the ones actually being compared
# against each other and learned from. The other three (carry_reminder,
# system_note, positive_association) still move consecutive_quiet_days,
# but they don't feed bandit_state — nothing is competing against them
# for a slot, so there's no "which one worked better" to track.
COMPETING_ARMS = {"cue", "habit_pairing", "log_prompt"}


def _get_message_type_record(session, user_id, message_type):
    """The one lookup every success/failure branch needs: this user's
    win/loss record for this particular message type, so far."""
    return (
        session.query(BanditState)
        .filter(BanditState.user_id == user_id, BanditState.arm == message_type)
        .first()
    )


def _mark_success(session, row: MessageLog):
    """A reply landed. Close the loop, and reward the message type
    that earned it."""
    row.counted_success = True

    user = session.query(User).filter(User.user_id == row.user_id).first()
    if user is not None:
        user.consecutive_quiet_days = 0

    if row.arm in COMPETING_ARMS:
        type_record = _get_message_type_record(session, row.user_id, row.arm)
        if type_record is not None:
            type_record.successes += 1

    # log_prompt is the one type that explicitly asked for something —
    # a logged amount. Acknowledging it closes a real conversational
    # loop ("I heard you"), even though it changes no stored numbers.
    # The other types are passive nudges; acknowledging a cue reply
    # would be noise, not closure, so we don't.
    if row.arm == "log_prompt":
        send_message(
            user_id=row.user_id,
            arm="log_prompt",
            content=f"got it — thanks for logging: {row.reply_content!r}",
        )


def _mark_failure(session, row: MessageLog):
    """No reply, even after the follow-up. This is the only place
    counted_success ever becomes False — never on the first missed
    window, only the second."""
    row.counted_success = False

    user = session.query(User).filter(User.user_id == row.user_id).first()
    if user is not None:
        user.consecutive_quiet_days += 1

    if row.arm in COMPETING_ARMS:
        type_record = _get_message_type_record(session, row.user_id, row.arm)
        if type_record is not None:
            type_record.failures += 1


def _send_retry(row: MessageLog):
    """Reuses the mock channel from Goal 2 — from the user's side,
    a retry is just another message arriving."""
    send_message(
        user_id=row.user_id,
        arm=row.arm,
        content="just checking in — still there?",
    )


def resolve_pending_messages():
    """
    The actual job. Walks every unresolved message_log row and, for
    the ones whose window has genuinely closed, decides its fate.

    Deliberately checks for a reply *first* — the good outcome — before
    ever asking "has this failed." A late reply still counts as success
    even if it arrived after a retry already went out.
    """
    session = SessionLocal()
    now = datetime.utcnow()

    try:
        pending = (
            session.query(MessageLog)
            .filter(MessageLog.counted_success.is_(None))
            .all()
        )

        for row in pending:
            if row.replied_at is not None:
                _mark_success(session, row)
                continue

            elapsed = now - row.sent_at

            if not row.retry_sent:
                if elapsed >= RESPONSE_WINDOW:
                    row.retry_sent = True
                    _send_retry(row)
                # else: first window hasn't even closed yet. Leave it.

            else:
                # Already got one follow-up. Has a second window's
                # worth of time passed since the original send?
                # (Approximated as 2x the window from sent_at, rather
                # than timing precisely from the retry — simpler to
                # reason about, and close enough at this stage.)
                if elapsed >= (RESPONSE_WINDOW * 2):
                    _mark_failure(session, row)
                # else: still waiting out the second window.

        session.commit()
    finally:
        session.close()