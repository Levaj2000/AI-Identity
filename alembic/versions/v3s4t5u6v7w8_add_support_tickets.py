"""Add support_tickets and ticket_comments tables.

Creates the support ticket system for customer support:
- support_tickets: Main ticket table with status, priority, category
- ticket_comments: Comment thread for each ticket
- Relationships to users, organizations, and agents for context

Revision ID: v3s4t5u6v7w8
Revises: u2r3s4t5u6v7
Create Date: 2026-04-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "v3s4t5u6v7w8"
down_revision = "u2r3s4t5u6v7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create support_tickets table
    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_number", sa.String(length=20), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("related_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_audit_log_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticket_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            name=op.f("fk_support_tickets_assigned_to_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_support_tickets_org_id_organizations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_agent_id"],
            ["agents.id"],
            name=op.f("fk_support_tickets_related_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_support_tickets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_support_tickets")),
        sa.UniqueConstraint("ticket_number", name=op.f("uq_support_tickets_ticket_number")),
    )
    
    # Create indexes for support_tickets
    op.create_index(
        op.f("ix_support_tickets_assigned_to_user_id"),
        "support_tickets",
        ["assigned_to_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_created_at"),
        "support_tickets",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_org_id"),
        "support_tickets",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_priority"),
        "support_tickets",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_status"),
        "support_tickets",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_ticket_number"),
        "support_tickets",
        ["ticket_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_support_tickets_user_id"),
        "support_tickets",
        ["user_id"],
        unique=False,
    )
    
    # Composite indexes for common queries
    op.create_index(
        "idx_tickets_user_org",
        "support_tickets",
        ["user_id", "org_id"],
        unique=False,
    )
    op.create_index(
        "idx_tickets_status_priority",
        "support_tickets",
        ["status", "priority"],
        unique=False,
    )

    # Create ticket_comments table
    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["support_tickets.id"],
            name=op.f("fk_ticket_comments_ticket_id_support_tickets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ticket_comments_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_comments")),
    )
    
    # Create indexes for ticket_comments
    op.create_index(
        op.f("ix_ticket_comments_ticket_id"),
        "ticket_comments",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_comments_user_id"),
        "ticket_comments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_comments_ticket_created",
        "ticket_comments",
        ["ticket_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop ticket_comments table and indexes
    op.drop_index("idx_comments_ticket_created", table_name="ticket_comments")
    op.drop_index(op.f("ix_ticket_comments_user_id"), table_name="ticket_comments")
    op.drop_index(op.f("ix_ticket_comments_ticket_id"), table_name="ticket_comments")
    op.drop_table("ticket_comments")
    
    # Drop support_tickets table and indexes
    op.drop_index("idx_tickets_status_priority", table_name="support_tickets")
    op.drop_index("idx_tickets_user_org", table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_user_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_ticket_number"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_status"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_priority"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_org_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_created_at"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_assigned_to_user_id"), table_name="support_tickets")
    op.drop_table("support_tickets")

# Made with Bob
