import os

import firebase_admin
from firebase_admin import credentials,  firestore


cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()   # this is the piece that was missing — gives you the actual Firestore handle


"""
firestore_tools.py — the 5 tools our service exposes for reading/writing
the main app's user data. All take a phone_number (our identity key),
resolve it to a firebase_uid via our own db, then talk to Firestore.

Tools:
    get_user_container(phone_number)
    log_water(phone_number, amount, drink_type="Water")
    get_remaining_goal(phone_number)
    get_analytics(phone_number, days=7)
    link_user_by_email(phone_number, email)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.db.repo import get_user_by_phone, set_firebase_uid


@dataclass
class ToolResult:
    failed: bool
    data: Optional[dict] = None
    error: str = ""


def _resolve_uid(phone_number: str) -> Optional[str]:
    user = get_user_by_phone(phone_number)
    if user is None or user.firebase_uid is None:
        return None
    return user.firebase_uid


def get_user_container(phone_number: str) -> ToolResult:
    uid = _resolve_uid(phone_number)
    if uid is None:
        return ToolResult(failed=True, error="user not linked to a Firestore account yet")

    docs = db.collection("users").document(uid).collection("user_containers").stream()
    containers = [{"id": d.id, **d.to_dict()} for d in docs]

    if not containers:
        return ToolResult(failed=True, error=f"no user_containers found for uid={uid}")
    return ToolResult(failed=False, data={"containers": containers})


def log_water(phone_number: str, amount: int, drink_type: str = "Water") -> ToolResult:
    uid = _resolve_uid(phone_number)
    if uid is None:
        return ToolResult(failed=True, error="user not linked to a Firestore account yet")

    now = datetime.now()
    entry = {
        "amount": amount,
        "drinkType": drink_type,
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "userId": uid,
    }
    db.collection("users").document(uid).collection("waterLogs").add(entry)
    return ToolResult(failed=False, data=entry)


def get_remaining_goal(phone_number: str) -> ToolResult:
    uid = _resolve_uid(phone_number)
    if uid is None:
        return ToolResult(failed=True, error="user not linked to a Firestore account yet")

    user_doc = db.collection("users").document(uid).get()
    if not user_doc.exists:
        return ToolResult(failed=True, error=f"no Firestore user doc for uid={uid}")
    daily_goal = user_doc.to_dict().get("dailyGoal", 0)

    today = datetime.now().strftime("%Y-%m-%d")
    logs = db.collection("users").document(uid).collection("waterLogs") \
        .where("date", "==", today).stream()
    total = sum(log.to_dict().get("amount", 0) for log in logs)

    return ToolResult(failed=False, data={
        "daily_goal": daily_goal,
        "total_so_far": total,
        "remaining": max(daily_goal - total, 0),
    })


def get_analytics(phone_number: str, days: int = 7) -> ToolResult:
    uid = _resolve_uid(phone_number)
    if uid is None:
        return ToolResult(failed=True, error="user not linked to a Firestore account yet")

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    logs = db.collection("users").document(uid).collection("waterLogs") \
        .where("date", ">=", cutoff).stream()

    totals_by_day = {}
    for log in logs:
        entry = log.to_dict()
        d = entry.get("date")
        totals_by_day[d] = totals_by_day.get(d, 0) + entry.get("amount", 0)

    days_logged = len(totals_by_day)
    avg_per_day = sum(totals_by_day.values()) / days_logged if days_logged else 0

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_total = totals_by_day.get(today_str, 0)

    return ToolResult(failed=False, data={
        "today": today_total,
        "days_logged": days_logged,
        "days_in_window": days,
        "avg_ml_per_logged_day": round(avg_per_day),
        "totals_by_day": totals_by_day,
    })


def link_user_by_email(phone_number: str, email: str) -> ToolResult:
    matches = list(db.collection("users").where("email", "==", email).limit(1).stream())
    if not matches:
        return ToolResult(failed=True, error="no Firestore user found with that email")

    uid = matches[0].id
    result = set_firebase_uid(phone_number, uid)
    if result.failed:
        return ToolResult(failed=True, error=result.error)
    return ToolResult(failed=False, data={"firebase_uid": uid})