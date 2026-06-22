"""Add audit_checkpoints for signed Merkle Evidence Anchor checkpoints.

#408 (Evidence Anchor). One row per signed checkpoint over a contiguous
batch of an org's audit_log rows. The DSSE envelope in the JSONB column is
the authoritative artifact; mirrored columns exist for indexing. Unique
(org_id, first_audit_id) keeps batches contiguous and non-overlapping so the
worker is idempotent and "find the checkpoint covering row N" is a range scan.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-22
"""

import sqlalchemy as sa

from alembic import op

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_checkpoints",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("tree_size", sa.Integer(), nullable=False),
        sa.Column("first_audit_id", sa.Integer(), nullable=False),
        sa.Column("last_audit_id", sa.Integer(), nullable=False),
        sa.Column("merkle_root", sa.String(64), nullable=False),
        # Frozen, ordered batch — purge-resilient. audit_log_ids maps an
        # event to its leaf index; leaves is the ordered entry_hash list the
        # Merkle tree was built over, so a proof rebuilds from leaves alone.
        sa.Column(
            "audit_log_ids",
            sa.dialects.postgresql.ARRAY(sa.Integer()),
            nullable=False,
        ),
        sa.Column(
            "leaves",
            sa.dialects.postgresql.ARRAY(sa.String()),
            nullable=False,
        ),
        sa.Column("signer_key_id", sa.String(512), nullable=False),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # The full signed DSSE checkpoint envelope — authoritative artifact.
        sa.Column(
            "envelope",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "first_audit_id", name="uq_checkpoint_org_first"),
    )

    op.create_index(
        "ix_audit_checkpoints_org_id",
        "audit_checkpoints",
        ["org_id"],
    )
    op.create_index(
        "ix_audit_checkpoint_range",
        "audit_checkpoints",
        ["org_id", "first_audit_id", "last_audit_id"],
    )
    op.create_index(
        "ix_audit_checkpoint_created",
        "audit_checkpoints",
        ["org_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_checkpoint_created", table_name="audit_checkpoints")
    op.drop_index("ix_audit_checkpoint_range", table_name="audit_checkpoints")
    op.drop_index("ix_audit_checkpoints_org_id", table_name="audit_checkpoints")
    op.drop_table("audit_checkpoints")
