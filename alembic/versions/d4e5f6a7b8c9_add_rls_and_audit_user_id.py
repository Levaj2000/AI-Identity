"""Add RLS policies and audit_log.user_id for cross-tenant isolation.

Defense-in-depth: PostgreSQL Row Level Security enforces tenant boundaries
at the database layer, backing up the application-layer isolation in
get_user_agent(). Even if an ORM bug or raw SQL bypasses the app layer,
the database itself will filter rows by user_id.

Phase A: Add user_id column to audit_log + backfill from agents table.
Phase B: Enable RLS with FORCE on all 5 tenant tables.
Phase C: Create tenant isolation + service bypass policies (10 total).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

# Tables that need RLS policies
RLS_TABLES = ["agents", "agent_keys", "policies", "upstream_credentials", "audit_log"]

# Tables with direct user_id column
DIRECT_USER_ID_TABLES = ["agents", "audit_log"]

# Tables that scope through agent_id → agents.user_id
INDIRECT_USER_ID_TABLES = ["agent_keys", "policies", "upstream_credentials"]


def upgrade() -> None:
    """Add user_id to audit_log, enable RLS, create tenant isolation policies."""
    dialect = op.get_bind().dialect.name

    # ── Phase A: Add user_id to audit_log + backfill ────────────────────
    op.add_column("audit_log", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])

    # Backfill user_id from the agents table
    op.execute(
        "UPDATE audit_log SET user_id = agents.user_id "
        "FROM agents WHERE audit_log.agent_id = agents.id "
        "AND audit_log.user_id IS NULL"
    )

    # ── Phase B & C: RLS (PostgreSQL only) ──────────────────────────────
    if dialect != "postgresql":
        return

    # Phase B: Enable RLS with FORCE on all tables
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # Phase C: Create policies — 2 per table (PERMISSIVE OR semantics)

    # Direct user_id tables: agents, audit_log
    for table in DIRECT_USER_ID_TABLES:
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL "
            f"USING (user_id = current_setting('app.current_user_id', true)::uuid) "
            f"WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)"
        )

    # Indirect tables: agent_keys, policies, upstream_credentials
    for table in INDIRECT_USER_ID_TABLES:
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL "
            f"USING (agent_id IN ("
            f"  SELECT id FROM agents "
            f"  WHERE user_id = current_setting('app.current_user_id', true)::uuid"
            f")) "
            f"WITH CHECK (agent_id IN ("
            f"  SELECT id FROM agents "
            f"  WHERE user_id = current_setting('app.current_user_id', true)::uuid"
            f"))"
        )

    # Service bypass policy (gateway runs without user context)
    for table in RLS_TABLES:
        op.execute(
            f"CREATE POLICY service_bypass ON {table} FOR ALL "
            f"USING (current_setting('app.is_service', true) = 'true') "
            f"WITH CHECK (current_setting('app.is_service', true) = 'true')"
        )


def downgrade() -> None:
    """Remove RLS policies and drop audit_log.user_id."""
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        # Drop policies
        for table in RLS_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
            op.execute(f"DROP POLICY IF EXISTS service_bypass ON {table}")

        # Disable RLS
        for table in RLS_TABLES:
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop user_id column
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_column("audit_log", "user_id")
