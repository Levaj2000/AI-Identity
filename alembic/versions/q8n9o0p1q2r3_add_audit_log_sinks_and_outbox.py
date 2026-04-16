"""Add audit_log_sinks + audit_log_outbox for forwarding audit events externally.

Phase 2A of the enterprise-logging program. Opt-in per org: when a sink is
configured, the writer enqueues one outbox row per event, and a worker
drains the outbox by POSTing signed batches to the sink URL.

No data backfill — brand-new tables. Existing audit rows don't generate
retroactive forwards; forwarding is strictly for events written *after* a
sink is created.

Revision ID: q8n9o0p1q2r3
Revises: p7m8n9o0p1q2
Create Date: 2026-04-15
"""

import sqlalchemy as sa

from alembic import op

revision = "q8n9o0p1q2r3"
down_revision = "p7m8n9o0p1q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── audit_log_sinks ────────────────────────────────────────────
    op.create_table(
        "audit_log_sinks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="webhook"),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(128), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "filter",
            sa.JSON().with_variant(
                sa.dialects.postgresql.JSONB(), "postgresql"
            ),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("circuit_opened_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_audit_log_sinks_org_enabled",
        "audit_log_sinks",
        ["org_id", "enabled"],
    )

    # ── audit_log_outbox ───────────────────────────────────────────
    op.create_table(
        "audit_log_outbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("audit_log_id", sa.Integer(), nullable=False),
        sa.Column("sink_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["audit_log_id"], ["audit_log.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sink_id"], ["audit_log_sinks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_audit_log_outbox_audit_log_id",
        "audit_log_outbox",
        ["audit_log_id"],
    )
    op.create_index(
        "ix_audit_log_outbox_sink_id",
        "audit_log_outbox",
        ["sink_id"],
    )
    op.create_index(
        "ix_audit_log_outbox_org_id",
        "audit_log_outbox",
        ["org_id"],
    )
    op.create_index(
        "ix_audit_log_outbox_due",
        "audit_log_outbox",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_audit_log_outbox_sink_status",
        "audit_log_outbox",
        ["sink_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_outbox_sink_status", table_name="audit_log_outbox")
    op.drop_index("ix_audit_log_outbox_due", table_name="audit_log_outbox")
    op.drop_index("ix_audit_log_outbox_org_id", table_name="audit_log_outbox")
    op.drop_index("ix_audit_log_outbox_sink_id", table_name="audit_log_outbox")
    op.drop_index("ix_audit_log_outbox_audit_log_id", table_name="audit_log_outbox")
    op.drop_table("audit_log_outbox")

    op.drop_index("ix_audit_log_sinks_org_enabled", table_name="audit_log_sinks")
    op.drop_table("audit_log_sinks")
