"""Add compliance_exports table for async export job records.

Milestone #34 — foundation for the compliance export builder. Schema
per ADR-002 Data Model section. The authoritative artifact is the ZIP
archive referenced by archive_url; this row mirrors the DSSE
manifest envelope + metadata for indexing and admin surfaces.

Revision ID: t1q2r3s4t5u6
Revises: s0p1q2r3s4t5
Create Date: 2026-04-23
"""

import sqlalchemy as sa

from alembic import op

revision = "t1q2r3s4t5u6"
down_revision = "s0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_exports",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("profile", sa.String(length=40), nullable=False),
        sa.Column(
            "audit_period_start",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "audit_period_end",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "agent_ids",
            sa.dialects.postgresql.ARRAY(sa.dialects.postgresql.UUID(as_uuid=True)).with_variant(
                sa.JSON(), "sqlite"
            ),
            nullable=True,
        ),
        sa.Column(
            "agent_ids_hash",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress_pct", sa.Integer(), nullable=True),
        sa.Column("archive_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "archive_url_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.Column("archive_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "manifest_envelope",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("archive_storage_path", sa.String(length=2048), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_compliance_exports"),
        sa.UniqueConstraint(
            "org_id",
            "profile",
            "audit_period_start",
            "audit_period_end",
            "agent_ids_hash",
            "status",
            name="uq_compliance_export_inflight",
        ),
    )
    op.create_index(
        "ix_compliance_exports_org_id",
        "compliance_exports",
        ["org_id"],
    )
    op.create_index(
        "ix_compliance_exports_status",
        "compliance_exports",
        ["status"],
    )
    op.create_index(
        "ix_compliance_exports_org_created_at",
        "compliance_exports",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_compliance_exports_org_status",
        "compliance_exports",
        ["org_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_exports_org_status", table_name="compliance_exports")
    op.drop_index("ix_compliance_exports_org_created_at", table_name="compliance_exports")
    op.drop_index("ix_compliance_exports_status", table_name="compliance_exports")
    op.drop_index("ix_compliance_exports_org_id", table_name="compliance_exports")
    op.drop_table("compliance_exports")
