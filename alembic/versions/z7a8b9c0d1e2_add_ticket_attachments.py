"""add ticket attachments

Revision ID: z7a8b9c0d1e2
Revises: y6w8x9y0z1a2
Create Date: 2026-04-30 19:36:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "z7a8b9c0d1e2"
down_revision = "y6w8x9y0z1a2"
branch_labels = None
depends_on = None


def upgrade():
    # Use raw SQL with IF NOT EXISTS for idempotent migration —
    # production runs Base.metadata.create_all() at app startup, which
    # may have already created the table before this migration runs.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ticket_attachments (
            id UUID NOT NULL,
            ticket_id UUID NOT NULL,
            comment_id UUID,
            user_id UUID,
            org_id UUID NOT NULL,
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            size_bytes BIGINT NOT NULL,
            sha256 VARCHAR(64) NOT NULL,
            storage_path VARCHAR(500) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            deleted_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id),
            FOREIGN KEY(comment_id) REFERENCES ticket_comments (id) ON DELETE CASCADE,
            FOREIGN KEY(org_id) REFERENCES organizations (id) ON DELETE CASCADE,
            FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL,
            UNIQUE (storage_path)
        )
    """)

    # All indexes use IF NOT EXISTS for the same reason
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_ticket_id "
        "ON ticket_attachments (ticket_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_comment_id "
        "ON ticket_attachments (comment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_user_id "
        "ON ticket_attachments (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_org_id "
        "ON ticket_attachments (org_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_ticket_created "
        "ON ticket_attachments (ticket_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_org_created "
        "ON ticket_attachments (org_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_attachments_deleted "
        "ON ticket_attachments (deleted_at)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_deleted")
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_org_created")
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_ticket_created")
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_org_id")
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_user_id")
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_comment_id")
    op.execute("DROP INDEX IF EXISTS ix_ticket_attachments_ticket_id")
    op.execute("DROP TABLE IF EXISTS ticket_attachments")
