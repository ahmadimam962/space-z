"""
Database Connection Module
This module sets up the SQLAlchemy database engine, session factory,
and declarative base for ORM models.
It also provides the `get_db` dependency used by FastAPI endpoints
to inject database sessions with automatic cleanup.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.config import settings


# ==========================================
# Database Engine & Session Setup
# ==========================================
# Create the SQLAlchemy engine with the database URL from settings.
# pool_pre_ping=True ensures stale connections are detected and refreshed.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

# Session factory - creates new database sessions for each request.
# autocommit=False: transactions must be explicitly committed.
# autoflush=False: changes aren't auto-flushed before queries.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base class for all ORM models.
Base = declarative_base()


# ==========================================
# Dependency Injection
# ==========================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.
    The session is automatically closed after the request completes,
    even if an exception occurs (via the finally block).

    Yields:
        Session: An active SQLAlchemy database session.

    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()