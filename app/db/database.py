# this is the file responsible for creating the database connection and session management for SQLAlchemy. it defines the database URL, creates an engine, and sets up a session factory for interacting with the database. it also defines a base class for declarative models.

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()