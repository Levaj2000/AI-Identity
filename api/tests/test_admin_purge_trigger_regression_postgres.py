"""Postgres regression tests for the audit_log trigger toggle in admin purge.

Issue #218 / PR #263: ``purge_revoked_agents`` and ``purge_single_agent`` in
``api/app/routers/admin.py`` temporarily disable the ``audit_log_no_update``
trigger before denormalizing ``agent_name`` into ``audit_log`` rows, then
re-enable it. Before #263, an exception inside the denormalization step would
skip the re-enable, leaving the SOC 2 append-only control disabled until
someone noticed and re-enabled it manually.

These tests force a Python-level exception inside the denormalization step
and assert the trigger is still enabled afterwards. They require Postgres
because:

* ``ALTER TABLE ... DISABLE/ENABLE TRIGGER`` is Postgres-specific DDL.
* The ``audit_log_no_update`` trigger is created by the Alembic migration
  ``a1b2c3d4e5f6_add_audit_integrity_chain.py`` and is skipped on SQLite.
* The check reads ``pg_trigger.tgenabled`` directly.

Per ``.bob/rules-code/AGENTS.md`` — "Postgres-Specific Features Require
Postgres-Backed Tests" — these tests are gated behind the ``postgres`` marker.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.app.routers.admin import purge_revoked_agents, purge_single_agent
from common.models import User
from common.models.agent import Agent, AgentStatus

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def audit_trigger(postgres_engine):
    """Create the ``audit_log_no_update`` trigger in the test database.

    ``Base.metadata.create_all`` (used by the shared ``postgres_engine``
    fixture) doesn't run Alembic migrations, so the Postgres-only
    append-only trigger isn't created automatically. Re-create it each
    test so we start from a known-enabled state regardless of what the
    previous test left behind.
    """
    with postgres_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION audit_log_immutable()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_log is append-only: % not permitted', TG_OP;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        conn.execute(text("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log"))
        conn.execute(
            text(
                """
                CREATE TRIGGER audit_log_no_update
                BEFORE UPDATE ON audit_log
                FOR EACH ROW
                EXECUTE FUNCTION audit_log_immutable();
                """
            )
        )
    yield


# ── Helpers ──────────────────────────────────────────────────────────


def _trigger_enabled(db: Session) -> bool:
    """Return True iff ``audit_log_no_update`` is currently enabled.

    ``pg_trigger.tgenabled`` is ``'O'`` for origin/enabled, ``'D'`` for disabled.
    The read happens in the caller's session so an uncommitted ``ALTER TABLE``
    is visible — that's exactly what we want to assert against.
    """
    state = db.execute(
        text(
            "SELECT tgenabled FROM pg_trigger "
            "WHERE tgname = 'audit_log_no_update' "
            "  AND tgrelid = 'audit_log'::regclass"
        )
    ).scalar_one()
    return state != "D"


def _make_admin(db: Session) -> User:
    admin = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4()}",
        role="admin",
        tier="enterprise",
    )
    db.add(admin)
    db.commit()
    return admin


def _make_revoked_agent(db: Session, days_old: int) -> Agent:
    owner = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4()}",
        role="owner",
        tier="enterprise",
    )
    db.add(owner)
    db.flush()
    agent = Agent(
        id=uuid.uuid4(),
        user_id=owner.id,
        name=f"Test Agent {uuid.uuid4()}",
        status=AgentStatus.revoked.value,
        revoked_at=datetime.now(UTC) - timedelta(days=days_old),
        capabilities=[],
        metadata_={},
    )
    db.add(agent)
    db.commit()
    return agent


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.postgres
@pytest.mark.integration
def test_purge_revoked_agents_reenables_trigger_on_exception(postgres_db, audit_trigger):
    """purge_revoked_agents must re-enable audit_log_no_update if the
    denormalization loop raises mid-way (regression test for #218)."""
    admin = _make_admin(postgres_db)
    _make_revoked_agent(postgres_db, days_old=31)
    assert _trigger_enabled(postgres_db), "precondition: trigger should be enabled"

    # Inject a Python-level exception inside the denormalization loop by
    # patching Query.update. Using a non-DB exception keeps the Postgres
    # transaction in a healthy state so we can read pg_trigger immediately
    # afterwards (a SQLAlchemyError would put the txn in 'aborted' state and
    # any subsequent SELECT would fail with InFailedSqlTransaction).
    with (
        patch(
            "sqlalchemy.orm.Query.update",
            side_effect=RuntimeError("simulated denormalization failure"),
        ),
        pytest.raises(RuntimeError, match="simulated"),
    ):
        asyncio.run(purge_revoked_agents(_admin=admin, db=postgres_db, retention_days=30))

    assert _trigger_enabled(postgres_db), (
        "audit_log_no_update was left disabled after exception — "
        "the try/finally guard in api/app/routers/admin.py "
        "(purge_revoked_agents) has regressed (see #218 / PR #263)"
    )


@pytest.mark.postgres
@pytest.mark.integration
def test_purge_single_agent_reenables_trigger_on_exception(postgres_db, audit_trigger):
    """purge_single_agent must re-enable audit_log_no_update if the
    denormalization UPDATE raises (regression test for #218)."""
    admin = _make_admin(postgres_db)
    agent = _make_revoked_agent(postgres_db, days_old=1)
    assert _trigger_enabled(postgres_db)

    # purge_single_agent denormalizes via a raw `db.execute(text("UPDATE ..."))`
    # rather than `Query.update`. Patch Session.execute and raise only when the
    # UPDATE audit_log statement runs, so the surrounding DISABLE/ENABLE
    # ALTER TABLE calls and the cascade DELETEs still go through to Postgres.
    real_execute = Session.execute

    def selective_execute(self, statement, *args, **kwargs):
        sql = str(getattr(statement, "text", statement))
        if "UPDATE audit_log SET agent_name" in sql:
            raise RuntimeError("simulated denormalization failure")
        return real_execute(self, statement, *args, **kwargs)

    with (
        patch.object(Session, "execute", selective_execute),
        pytest.raises(RuntimeError, match="simulated"),
    ):
        asyncio.run(purge_single_agent(agent_id=str(agent.id), _admin=admin, db=postgres_db))

    assert _trigger_enabled(postgres_db), (
        "audit_log_no_update was left disabled after exception — "
        "the try/finally guard in api/app/routers/admin.py "
        "(purge_single_agent) has regressed (see #218 / PR #263)"
    )


# Made with Bob
