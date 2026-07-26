from .database import Base, SessionLocal, engine
from .models import HabitLibrary

ANCHOR_TEXTS = [
    "after you brush your teeth",
    "after you close your laptop for the day",
    "right after breakfast",
]


def create_and_seed():
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        existing = session.query(HabitLibrary).count()
        if existing == 0:
            session.add_all(
                [HabitLibrary(anchor_text=text) for text in ANCHOR_TEXTS]
            )
            session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    create_and_seed()
    print("Tables created and habit_library seeded.")