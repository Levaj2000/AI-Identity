"""Pytest fixtures for API tests — in-memory SQLite, test client, seed user."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, Uuid, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common.models import Agent, AgentKey, Base, KeyStatus, KeyType, User, get_db

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
TEST_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
TEST_API_KEY = "test-user-api-key-12345678"


def _create_test_agent(db_session, user, agent_id=None, status="active"):
    """Helper to create a test agent with an initial runtime key."""
    from common.auth.keys import generate_api_key, get_key_prefix, hash_key

    aid = agent_id or TEST_AGENT_ID
    agent = Agent(
        id=aid,
        user_id=user.id,
        name="Test Agent",
        status=status,
        capabilities=["chat_completion"],
        metadata_={},
    )
    db_session.add(agent)

    plaintext_key = generate_api_key(key_type="runtime")
    key = AgentKey(
        agent_id=aid,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        key_type=KeyType.runtime.value,
        status=KeyStatus.active.value,
    )
    db_session.add(key)
    db_session.commit()
    db_session.refresh(agent)
    return agent


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


@pytest.fixture(autouse=True)
def mock_internal_service_key(monkeypatch):
    """Set a test internal service key for cron endpoint tests."""
    from common.config.settings import settings

    monkeypatch.setattr(settings, "internal_service_key", "test-internal-key-xyz")


@pytest.fixture
def test_user(db_session):
    """Pre-created test user with organization."""
    from common.models import Organization

    # Create user first (without org_id)
    user = User(
        id=TEST_USER_ID,
        email=TEST_API_KEY,
        role="owner",
        tier="enterprise",  # Tests need unlimited quotas
    )
    db_session.add(user)
    db_session.flush()

    # Create organization
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000100")
    org = Organization(
        id=org_id,
        name="Test Organization",
        owner_id=user.id,
        tier="enterprise",
    )
    db_session.add(org)
    db_session.flush()

    # Wire up user.org_id
    user.org_id = org_id
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
    from common.models import Organization

    # Create user first (without org_id)
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        email="other-user-api-key-87654321",
        role="owner",
        tier="enterprise",  # Tests need unlimited quotas
    )
    db_session.add(user)
    db_session.flush()

    # Create organization
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000200")
    org = Organization(
        id=org_id,
        name="Other Organization",
        owner_id=user.id,
        tier="enterprise",
    )
    db_session.add(org)
    db_session.flush()

    # Wire up user.org_id
    user.org_id = org_id
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Admin user for testing admin-only operations."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        email="admin-api-key-99999999",
        role="admin",
        tier="enterprise",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mock_storage():
    """Mock storage backend for tests."""
    from datetime import UTC, datetime, timedelta
    from unittest.mock import AsyncMock

    from api.app.main import app
    from api.app.routers.attachment_cleanup_cron import get_storage as get_storage_cron
    from api.app.routers.attachments import get_storage

    mock = AsyncMock()
    mock.upload = AsyncMock(return_value="test/path/file.png")
    mock.download = AsyncMock()
    mock.generate_signed_url = AsyncMock(
        return_value=("https://example.com/signed-url", datetime.now(UTC) + timedelta(hours=1))
    )
    mock.delete = AsyncMock()
    mock.exists = AsyncMock(return_value=True)

    # Override FastAPI dependency injection
    app.dependency_overrides[get_storage] = lambda: mock
    app.dependency_overrides[get_storage_cron] = lambda: mock

    yield mock

    # Cleanup
    app.dependency_overrides.pop(get_storage, None)
    app.dependency_overrides.pop(get_storage_cron, None)


@pytest.fixture
def mock_magic(monkeypatch):
    """Stub libmagic so tests run without the system library."""
    from pathlib import Path

    def fake_detect(file_path: Path) -> str | None:
        """Return content type based on magic bytes (file content), not extension."""
        try:
            with open(file_path, "rb") as f:
                head = f.read(8)
        except Exception:
            return None

        # Detect by magic bytes (like real libmagic)
        if head[:2] == b"MZ":
            return "application/x-msdownload"  # Windows exe
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if head[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if head[:4] == b"%PDF":
            return "application/pdf"
        if head[:4] == b"GIF8":
            return "image/gif"
        if head[:4] == b"RIFF" and len(head) >= 12:
            # Read more to check for WEBP
            with open(file_path, "rb") as f:
                f.seek(8)
                webp_sig = f.read(4)
                if webp_sig == b"WEBP":
                    return "image/webp"
        if head[:2] == b"PK":
            return "application/zip"

        # Fallback to extension for text-like files
        ext = file_path.suffix.lower()
        return {
            ".txt": "text/plain",
            ".log": "text/plain",
            ".md": "text/markdown",
        }.get(ext)

    monkeypatch.setattr(
        "common.validation.file_upload._detect_content_type",
        fake_detect,
    )


@pytest.fixture
def mock_clamav(monkeypatch):
    """Stub ClamAV so tests run without the daemon."""
    from pathlib import Path

    def fake_scan(file_path: Path) -> tuple[bool, str | None]:
        """Return clean for most files, EICAR for test virus."""
        # Read first 68 bytes to check for EICAR test string
        try:
            with open(file_path, "rb") as f:
                content = f.read(68)
                if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
                    return False, "EICAR-Test-File"
        except Exception:
            pass
        return True, None

    monkeypatch.setattr(
        "common.security.virus_scan._scan_with_clamav",
        fake_scan,
    )


# ============================================================================
# Postgres fixtures for integration tests
# ============================================================================


@pytest.fixture(scope="session")
def postgres_container():
    """Spin up a real Postgres container for integration tests."""
    from testcontainers.postgres import PostgresContainer

    try:
        with PostgresContainer("postgres:15-alpine") as pg:
            yield pg
    except Exception as e:
        pytest.skip(f"Docker not available for testcontainers: {e}")


@pytest.fixture(scope="session")
def postgres_engine(postgres_container):
    """Create a Postgres engine using testcontainers. Schema is created once
    per session; per-test isolation happens via TRUNCATE in postgres_db."""
    from sqlalchemy import create_engine

    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def postgres_db(postgres_engine):
    """Postgres-backed DB session — TRUNCATE between tests for isolation.

    Using TRUNCATE CASCADE in reverse-dependency order avoids FK-ordering
    issues that drop_all hits on Postgres, and keeps the schema stable
    across the session so tests don't pay create_all/drop_all cost each run.
    """
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=postgres_engine)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        # Truncate all tables in reverse-dependency order with CASCADE
        # so FK chains don't block cleanup.
        with postgres_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


@pytest.fixture
def postgres_client(postgres_db):
    """FastAPI TestClient with Postgres database."""
    from api.app.main import app

    def _override_get_db():
        try:
            yield postgres_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(admin_user):
    """Auth headers for admin user."""
    return {"X-API-Key": admin_user.email}
