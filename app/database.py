# this is the file responsible for creating the database connection and session management for SQLAlchemy. it defines the database URL, creates an engine, and sets up a session factory for interacting with the database. it also defines a base class for declarative models.

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./bluedrop.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()