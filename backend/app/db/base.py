"""
SQLAlchemy Base class and model imports.

Import all models here so Alembic can auto-detect them for migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# NOTE: Model imports are in alembic/env.py to avoid circular imports at runtime
