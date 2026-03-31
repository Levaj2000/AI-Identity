"""Add agent_name column to audit_log table.

Denormalizes the agent name into audit logs so entries remain
meaningful after the agent record is hard-deleted during purge.

Backfills agent_name from agents table for existing rows.

Revision ID: k2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from alembic import op

revision = "k2g3h4i5j6k7"
down_revision = "k1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column("agent_name", sa.String(255), nullable=True),
    )

    # Backfill from agents table
    op.execute(
        "UPDATE audit_log SET agent_name = agents.name "
        "FROM agents WHERE audit_log.agent_id = agents.id AND audit_log.agent_name IS NULL"
    )


def downgrade() -> None:
    op.drop_column("audit_log", "agent_name")
