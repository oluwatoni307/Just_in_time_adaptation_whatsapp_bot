from app.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()

print("=== Proximal: reply rate per user/arm/day ===")
rows = session.execute(text("""
    SELECT user_id, arm, DATE(sent_at) as day,
           COUNT(*) as sent,
           SUM(CASE WHEN counted_success THEN 1 ELSE 0 END) as replied
    FROM message_log
    GROUP BY user_id, arm, DATE(sent_at)
""")).fetchall()
for r in rows:
    print(r)

print("\n=== Proximal: bandit standing per user ===")
rows = session.execute(text("""
    SELECT user_id, arm, successes, failures,
           successes * 1.0 / (successes + failures) as win_rate
    FROM bandit_state
""")).fetchall()
for r in rows:
    print(r)

print("\n=== Distal: daily intake trend ===")
rows = session.execute(text("""
    SELECT user_id, DATE(logged_at) as day, SUM(amount_ml) as total_ml
    FROM intake_log
    GROUP BY user_id, DATE(logged_at)
    ORDER BY user_id, day
""")).fetchall()
for r in rows:
    print(r)

session.close()