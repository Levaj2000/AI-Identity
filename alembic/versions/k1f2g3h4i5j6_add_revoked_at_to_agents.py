"""Add revoked_at timestamp to agents table.

Tracks when an agent was revoked, enabling retention-based purge
of revoked agents after a configurable period.

Backfills revoked_at = updated_at for all existing revoked agents.

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from alembic import op

revision = "k1f2g3h4i5j6"
down_revision = "j0e1f2g3h4i5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill: set revoked_at = updated_at for existing revoked agents
    op.execute(
        "UPDATE agents SET revoked_at = updated_at WHERE status = 'revoked' AND revoked_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("agents", "revoked_at")
