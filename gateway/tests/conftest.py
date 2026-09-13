"""Pytest fixtures for gateway tests — in-memory SQLite, test client, seed data."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, Uuid, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common.models import Agent, Base, Policy, User, get_db

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
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()
        elif isinstance(column.type, UUID):
            column.type = Uuid()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixed UUIDs for deterministic tests
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
TEST_AGENT_ID_2 = uuid.UUID("00000000-0000-0000-0000-000000000020")


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
        email="test-gateway-user@example.com",
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


@pytest.fixture
def test_policy(db_session, test_agent):
    """Active policy allowing /v1/* endpoints with POST method."""
    policy = Policy(
        agent_id=test_agent.id,
        rules={
            "allowed_endpoints": ["/v1/*"],
            "allowed_methods": ["POST", "GET"],
        },
        version=1,
        is_active=True,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def suspended_agent(db_session, test_user):
    """A suspended agent for testing inactive enforcement."""
    agent = Agent(
        id=TEST_AGENT_ID_2,
        user_id=test_user.id,
        name="Suspended Agent",
        status="suspended",
        capabilities=[],
        metadata={},
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the module-level rate limiter between tests.

    Prevents request counts from leaking between tests.
    """
    from gateway.app.rate_limiter import rate_limiter

    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def wide_rate_limit_window():
    """Widen the limiter's sliding window for tests that exhaust a limit.

    The window defaults to one second while the per-IP limit is 100, so a test
    that sends 100 real requests and asserts the 101st is throttled only passes
    when all 100 round trips finish inside that second. On a loaded runner they
    do not: the earliest timestamps fall outside the window, the count drops
    back under the limit, and the request the test expects to be denied is
    correctly allowed. The assertion is then about machine speed rather than
    about rate limiting.

    Widening the window removes the clock from the test without changing what
    is being verified: the limit, the counting and the 429 path are untouched,
    and entries simply cannot age out mid-burst. Tests that verify expiry
    itself drive their own RateLimiter instance and must not use this fixture.
    """
    from gateway.app.rate_limiter import rate_limiter

    backends = {id(b): b for b in (rate_limiter._backend, rate_limiter._fallback)}.values()
    originals = [(b, b._window_seconds) for b in backends]
    for backend, _ in originals:
        backend._window_seconds = 3600.0
    try:
        yield
    finally:
        for backend, original in originals:
            backend._window_seconds = original


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with DB override."""
    from gateway.app import main as gateway_main
    from gateway.app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    # The /health probe opens its own session via the module-global
    # SessionLocal (bound to the real engine), which bypasses the get_db
    # dependency override. Point it at the in-memory test DB so health
    # checks don't try to reach the production database, and clear the
    # 10s probe cache so a prior failure doesn't leak in.
    original_session_local = gateway_main.SessionLocal
    gateway_main.SessionLocal = TestSessionLocal
    gateway_main._db_probe_cache.update({"ok": False, "error": None, "ts": 0.0})

    with TestClient(app) as c:
        yield c

    gateway_main.SessionLocal = original_session_local
    gateway_main._db_probe_cache.update({"ok": False, "error": None, "ts": 0.0})
    app.dependency_overrides.clear()
