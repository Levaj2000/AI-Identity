"""Pytest fixtures for common/ tests — in-memory SQLite for DB-backed tests."""

import uuid

import pytest
from sqlalchemy import JSON, Uuid, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common.models import Agent, Base, User

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Remap PostgreSQL-specific types to SQLite-compatible types
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()
        elif isinstance(column.type, UUID):
            column.type = Uuid()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


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
        email="test-common-user@example.com",
        role="owner",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_agent(db_session, test_user):
    """Pre-created active agent."""
    agent = Agent(
        id=TEST_AGENT_ID,
        user_id=test_user.id,
        name="Test Agent",
        status="active",
        capabilities=["chat_completion"],
        metadata={},
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent
