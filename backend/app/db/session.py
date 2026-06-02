"""
Database session management.

Provides database engine, session factory, and dependency injection for FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings


# Create database engine with connection pooling.
#
# NOTE: DATABASE_URL points at the Supabase Supavisor SESSION pooler, which caps
# concurrent server connections per project. Each app process holds up to
# pool_size + max_overflow connections, so keep the ceiling modest and recycle
# idle connections (the pooler drops them after a timeout, which pool_pre_ping
# then detects). pool_timeout fails fast instead of hanging a request when the
# pool is saturated.
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,   # Verify/replace dead connections before using
    pool_recycle=1800,    # Recycle connections after 30 min to dodge pooler idle-close
    pool_timeout=30,      # Fail fast if the pool is exhausted rather than hang
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
