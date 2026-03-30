"""Add approval_requests table for human-in-the-loop review.

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-03-30

Enterprise tier feature: paused gateway requests awaiting human approval.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "j0e1f2g3h4i5"
down_revision = "i9d0e1f2g3h4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.String(2048), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("request_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Standard lookup indexes
    op.create_index("ix_approval_requests_agent_id", "approval_requests", ["agent_id"])
    op.create_index("ix_approval_requests_user_id", "approval_requests", ["user_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])

    # Composite indexes for workflow queries
    op.create_index(
        "ix_approval_agent_status", "approval_requests", ["agent_id", "status"]
    )
    op.create_index(
        "ix_approval_user_status", "approval_requests", ["user_id", "status"]
    )

    # Partial index for expire cleanup (only pending rows)
    op.execute(
        "CREATE INDEX ix_approval_expires_pending ON approval_requests (expires_at) "
        "WHERE status = 'pending'"
    )


def downgrade() -> None:
    op.drop_table("approval_requests")
