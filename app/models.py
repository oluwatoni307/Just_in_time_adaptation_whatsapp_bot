# models.py
# this file defines the SQLAlchemy models for the application. it includes the User, IntakeLog, and BanditState models, along with the BanditArm enum and a function to determine the default minimum interval days based on the arm type. these models represent the structure of the database tables and their relationships.


import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)

from .database import Base

class User(Base):
    """Represents a user in the system.
    parameters:
        user_id (int): The unique identifier for the user.
        onboarded_at (datetime): The timestamp when the user was onboarded.
        consecutive_quiet_days (int): The number of consecutive days the user has not logged any intake.
        daily_goal_ml (int): The user's daily intake goal in milliliters.
        habit_anchor (str): The user's habit anchor, which can be used to trigger reminders or notifications.
        
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    onboarded_at = Column(DateTime, nullable=False)
    consecutive_quiet_days = Column(Integer, nullable=False, default=0)
    daily_goal_ml = Column(Integer, nullable=False)
    habit_anchor = Column(String, nullable=True)
    
class IntakeLog(Base):
    __tablename__ = "intake_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    logged_at = Column(DateTime, nullable=False)
    amount_ml = Column(Integer, nullable=False)
    source_message_log_id = Column(
        Integer, ForeignKey("message_log.log_id"), nullable=True
    )
    
    
class BanditArm(str, enum.Enum):
    cue = "cue"
    habit_pairing = "habit_pairing"
    log_prompt = "log_prompt"
    carry_reminder = "carry_reminder"
    system_note = "system_note"
    positive_association = "positive_association"


MIN_INTERVAL_DAYS_BY_ARM = {
    BanditArm.cue: 0,
    BanditArm.habit_pairing: 0,
    BanditArm.log_prompt: 0,
    BanditArm.carry_reminder: 1,
    BanditArm.system_note: 5,
    BanditArm.positive_association: 3,
}


def _default_min_interval_days(context):
    arm = context.get_current_parameters().get("arm")
    return MIN_INTERVAL_DAYS_BY_ARM.get(arm, 0)


class BanditState(Base):
    __tablename__ = "bandit_state"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    arm = Column(Enum(BanditArm), nullable=False)
    successes = Column(Integer, nullable=False, default=1)
    failures = Column(Integer, nullable=False, default=1)
    min_interval_days = Column(
        Integer, nullable=False, default=_default_min_interval_days
    )
    last_sent_at = Column(DateTime, nullable=True)
    
class TimeBucket(str, enum.Enum):
    morning = "morning"
    midday = "midday"
    afternoon = "afternoon"
    evening = "evening"


class TimeBanditState(Base):
    __tablename__ = "time_bandit_state"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    time_bucket = Column(Enum(TimeBucket), nullable=False)
    successes = Column(Integer, nullable=False, default=1)
    failures = Column(Integer, nullable=False, default=1)
    
    
class MessageLog(Base):
    __tablename__ = "message_log"

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    arm = Column(Enum(BanditArm), nullable=False)
    sent_at = Column(DateTime, nullable=False)
    replied_at = Column(DateTime, nullable=True)
    reply_content = Column(String, nullable=True)
    counted_success = Column(Boolean, nullable=True)
    retry_sent = Column(Boolean, nullable=False, default=False)
    
    
    
class HabitLibrary(Base):
    __tablename__ = "habit_library"

    habit_id = Column(Integer, primary_key=True)
    anchor_text = Column(String, nullable=False)