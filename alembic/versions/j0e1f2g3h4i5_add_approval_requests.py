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
down_revision = "i9d0e1f2g3h5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS for idempotent migration
    op.execute("""
        CREATE TABLE IF NOT EXISTS approval_requests (
            id UUID NOT NULL PRIMARY KEY,
            agent_id UUID NOT NULL,
            user_id UUID NOT NULL,
            endpoint VARCHAR(2048) NOT NULL,
            method VARCHAR(10) NOT NULL,
            request_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            reviewer_id UUID,
            reviewer_note TEXT,
            resolved_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)

    # All indexes use IF NOT EXISTS for safety
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_agent_id ON approval_requests (agent_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_user_id ON approval_requests (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_status ON approval_requests (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_agent_status ON approval_requests (agent_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_user_status ON approval_requests (user_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_expires_pending ON approval_requests (expires_at) WHERE status = 'pending'")


def downgrade() -> None:
    op.drop_table("approval_requests")
