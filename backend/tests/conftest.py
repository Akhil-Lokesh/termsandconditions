"""
Pytest configuration and fixtures.

Provides test database, test client, and sample data fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db


# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite specific
)

# Create test session factory
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.

    Yields:
        Session: Database session
    """
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a test client with test database.

    Args:
        db: Database session fixture

    Yields:
        TestClient: FastAPI test client
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_path():
    """
    Provide path to sample PDF file.

    Returns:
        str: Path to sample PDF (create if doesn't exist)
    """
    # TODO: Create or provide path to sample PDF
    import os
    sample_path = "data/test_samples/sample_tc.pdf"
    os.makedirs(os.path.dirname(sample_path), exist_ok=True)
    return sample_path
