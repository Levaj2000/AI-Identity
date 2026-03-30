"""Add performance indexes for P95 latency reduction.

Adds composite indexes on hot-path queries:
- policies(agent_id, is_active, version DESC) — gateway policy lookup
- agents(user_id, status) — agent listing and compliance checks
- agent_keys(agent_id, status) — key lookups and compliance checks
- audit_log(user_id, created_at) — usage aggregation by user

Revision ID: i9d0e1f2g3h5
Revises: i9d0e1f2g3h4
Create Date: 2026-03-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "i9d0e1f2g3h5"
down_revision = "i9d0e1f2g3h4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All indexes use IF NOT EXISTS — safe to re-run if they were
    # previously created before the migration chain was fixed.

    # Critical: policy lookup in gateway enforce — every request hits this
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policies_agent_active_version "
        "ON policies (agent_id, is_active, version DESC)"
    )

    # Agent listing filtered by user + status
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agents_user_status "
        "ON agents (user_id, status)"
    )

    # Key lookups by agent + status (compliance checks, key validation)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_keys_agent_status "
        "ON agent_keys (agent_id, status)"
    )

    # Usage aggregation queries filter by user_id + date range
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_user_created "
        "ON audit_log (user_id, created_at)"
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_user_created", table_name="audit_log")
    op.drop_index("ix_agent_keys_agent_status", table_name="agent_keys")
    op.drop_index("ix_agents_user_status", table_name="agents")
    op.drop_index("ix_policies_agent_active_version", table_name="policies")
