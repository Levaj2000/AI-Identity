"""Pytest fixtures for API tests — in-memory SQLite, test client, seed user."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, Uuid, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common.models import Base, User, get_db

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Remap PostgreSQL-specific types to SQLite-compatible types
# JSONB → JSON, UUID → String(36)
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()
        elif isinstance(column.type, UUID):
            column.type = Uuid()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixed UUIDs for deterministic tests
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_API_KEY = "test-user-api-key-12345678"


@pytest.fixture(autouse=True)
def db_session():
    """Create all tables, yield a session, then drop everything."""
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Pre-created test user."""
    user = User(
        id=TEST_USER_ID,
        email=TEST_API_KEY,
        role="owner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session, test_user):
    """FastAPI TestClient with DB and auth overrides."""
    from api.app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Default auth headers for the test user."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def other_user(db_session):
    """A second user for testing ownership isolation."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="other-user-api-key-87654321",
        role="owner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
