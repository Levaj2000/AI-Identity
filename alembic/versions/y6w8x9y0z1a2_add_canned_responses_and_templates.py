"""Add canned_responses and ticket_templates tables.

Creates tables for support efficiency features:
- canned_responses: Pre-written responses for common questions
- ticket_templates: Pre-configured ticket templates for common scenarios

Revision ID: y6w8x9y0z1a2
Revises: x5u8v9w0x1y2
Create Date: 2026-04-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "y6w8x9y0z1a2"
down_revision = "x5u8v9w0x1y2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create canned_responses table
    op.create_table(
        "canned_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_canned_responses_created_by_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_canned_responses_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canned_responses")),
    )

    # Create indexes for canned_responses
    op.create_index(
        op.f("ix_canned_responses_org_id"),
        "canned_responses",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canned_responses_category"),
        "canned_responses",
        ["category"],
        unique=False,
    )
    op.create_index(
        "idx_canned_responses_org_category",
        "canned_responses",
        ["org_id", "category"],
        unique=False,
    )

    # Create ticket_templates table
    op.create_table(
        "ticket_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_template", sa.String(length=255), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("default_priority", sa.String(length=20), nullable=False),
        sa.Column("default_category", sa.String(length=50), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_ticket_templates_created_by_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_ticket_templates_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_templates")),
    )

    # Create indexes for ticket_templates
    op.create_index(
        op.f("ix_ticket_templates_org_id"),
        "ticket_templates",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_templates_name"),
        "ticket_templates",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    # Drop ticket_templates table and indexes
    op.drop_index(op.f("ix_ticket_templates_name"), table_name="ticket_templates")
    op.drop_index(op.f("ix_ticket_templates_org_id"), table_name="ticket_templates")
    op.drop_table("ticket_templates")

    # Drop canned_responses table and indexes
    op.drop_index("idx_canned_responses_org_category", table_name="canned_responses")
    op.drop_index(op.f("ix_canned_responses_category"), table_name="canned_responses")
    op.drop_index(op.f("ix_canned_responses_org_id"), table_name="canned_responses")
    op.drop_table("canned_responses")


# Made with Bob