from datetime import datetime

from app.database import SessionLocal
from app.models import BanditState, HabitLibrary, IntakeLog, MessageLog, TimeBanditState, User

results = []

def check(label, fn):
    try:
        fn()
        results.append((label, True, ""))
    except AssertionError as e:
        results.append((label, False, str(e)))
    except Exception as e:
        results.append((label, False, f"{type(e).__name__}: {e}"))

session = SessionLocal()

def check_all_tables_query():
    for model in [User, IntakeLog, BanditState, TimeBanditState, MessageLog, HabitLibrary]:
        session.query(model).all()

check("1. All six tables exist and can be queried with no errors", check_all_tables_query)

test_user = User(onboarded_at=datetime.utcnow(), consecutive_quiet_days=0, daily_goal_ml=2000)
session.add(test_user)
session.commit()

def check_bandit_defaults():
    bs = BanditState(user_id=test_user.user_id, arm="cue")
    session.add(bs)
    session.commit()
    session.refresh(bs)
    assert bs.successes == 1
    assert bs.failures == 1

check("2. bandit_state successes/failures default to 1/1", check_bandit_defaults)

def check_null_counted_success():
    ml = MessageLog(user_id=test_user.user_id, arm="log_prompt", sent_at=datetime.utcnow())
    session.add(ml)
    session.commit()
    session.refresh(ml)
    assert ml.counted_success is None

check("3. message_log.counted_success stays NULL", check_null_counted_success)

def check_join():
    row = session.query(User, BanditState).join(BanditState, BanditState.user_id == User.user_id).filter(User.user_id == test_user.user_id).first()
    assert row is not None

check("4. bandit_state JOIN users returns a result", check_join)

def check_habit_count():
    assert session.query(HabitLibrary).count() == 3

check("5. habit_library has exactly 3 rows", check_habit_count)

session.close()

for label, passed, err in results:
    print(f"[{'PASS' if passed else 'FAIL'}] {label}" + (f" -> {err}" if err else ""))