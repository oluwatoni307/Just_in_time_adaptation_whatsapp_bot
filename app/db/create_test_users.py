"""
One-off script: creates a single real test user (your number + email),
linked to Firestore. Since phone_number is now the primary key, only one
row can exist per number — to simulate different engagement states
(high/low/new), edit consecutive_quiet_days on this same row between test
runs rather than creating separate profiles.

Run once: python -m app.db.create_test_users
Re-run set_consecutive_quiet_days() separately to change engagement state.
"""

from app.db.repo import create_user
import app.util.hydration_service  as firestore_tools

PHONE_NUMBER = "08142156076"   # TODO: confirm E.164 format needed for real sends
EMAIL = "abdulghanniymajeed377@gmail.com"


def create_test_user():
    user = create_user(PHONE_NUMBER)  # seeds bandit state internally

    link_result = firestore_tools.link_user_by_email(PHONE_NUMBER, EMAIL)
    if link_result.failed:
        print(f"WARNING: could not link to Firestore: {link_result.error}")
    else:
        print(f"Linked to firebase_uid={link_result.data['firebase_uid']}")

    return user


if __name__ == "__main__":
    user = create_test_user()
    print(f"Created user_id={user.user_id}")