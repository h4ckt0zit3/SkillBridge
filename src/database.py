"""
database.py — SQLAlchemy engine, session factory, and Base declarative class.

Loads DATABASE_URL from environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env file from the project root
load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Create a .env file (see .env.example) with a valid PostgreSQL connection string."
    )

# Create the SQLAlchemy engine
# SQLite requires check_same_thread=False for FastAPI's threaded model
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory — each request gets its own session via dependency injection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for all ORM models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a database session and ensures
    it is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
