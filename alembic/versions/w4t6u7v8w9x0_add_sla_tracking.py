"""Add SLA tracking columns to support_tickets.

Adds columns for SLA due time, breach tracking, and escalation count.

Revision ID: w4t6u7v8w9x0
Revises: v3s4t5u6v7w8
Create Date: 2026-04-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "w4t6u7v8w9x0"
down_revision = "v3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add SLA tracking columns
    op.add_column(
        "support_tickets",
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "support_tickets",
        sa.Column("escalation_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add index for SLA queries (find overdue tickets)
    op.create_index(
        "idx_tickets_sla_due",
        "support_tickets",
        ["sla_due_at", "status"],
        unique=False,
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_tickets_sla_due", table_name="support_tickets")

    # Drop columns
    op.drop_column("support_tickets", "escalation_count")
    op.drop_column("support_tickets", "sla_breached")
    op.drop_column("support_tickets", "sla_due_at")


# Made with Bob