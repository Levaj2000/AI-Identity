"""Add max_escalations cap and original_sla_due_at tracking.

Adds original_sla_due_at to track first breach time for accurate hours_overdue.
Adds max_escalations constant (3) to prevent infinite escalation loops.

Revision ID: x5u8v9w0x1y2
Revises: w4t6u7v8w9x0
Create Date: 2026-04-30
"""

import sqlalchemy as sa

from alembic import op

revision = "x5u8v9w0x1y2"
down_revision = "w4t6u7v8w9x0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add original_sla_due_at to track first breach time
    op.add_column(
        "support_tickets",
        sa.Column("original_sla_due_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("support_tickets", "original_sla_due_at")


# Made with Bob