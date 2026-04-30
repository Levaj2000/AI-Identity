"""add ticket attachments

Revision ID: z7a8b9c0d1e2
Revises: y6w8x9y0z1a2
Create Date: 2026-04-30 19:36:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "z7a8b9c0d1e2"
down_revision = "y6w8x9y0z1a2"
branch_labels = None
depends_on = None


def upgrade():
    # Create ticket_attachments table
    op.create_table(
        "ticket_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["ticket_comments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["support_tickets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )

    # Create indexes
    op.create_index(
        "ix_ticket_attachments_ticket_id",
        "ticket_attachments",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_attachments_comment_id",
        "ticket_attachments",
        ["comment_id"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_attachments_user_id",
        "ticket_attachments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_attachments_org_id",
        "ticket_attachments",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_attachments_ticket_created",
        "ticket_attachments",
        ["ticket_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_attachments_org_created",
        "ticket_attachments",
        ["org_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_attachments_deleted",
        "ticket_attachments",
        ["deleted_at"],
        unique=False,
    )


def downgrade():
    # Drop indexes
    op.drop_index("ix_ticket_attachments_deleted", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_org_created", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_ticket_created", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_org_id", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_user_id", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_comment_id", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_ticket_id", table_name="ticket_attachments")

    # Drop table
    op.drop_table("ticket_attachments")

# Made with Bob
