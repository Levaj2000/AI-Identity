"""Indexes for the public Evidence Anchor checkpoint feed.

The feed (``GET /evidence-anchor/checkpoints``) orders the global history by
``signed_at`` and the split-view spot check looks up a checkpoint by
``merkle_root`` — both previously unindexed (existing indexes are all
org-scoped). Unauthenticated endpoints must not be able to trigger sequential
scans.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-24
"""

from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_checkpoint_signed_at",
        "audit_checkpoints",
        ["signed_at", "id"],
    )
    op.create_index(
        "ix_audit_checkpoint_merkle_root",
        "audit_checkpoints",
        ["merkle_root"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_checkpoint_merkle_root", table_name="audit_checkpoints")
    op.drop_index("ix_audit_checkpoint_signed_at", table_name="audit_checkpoints")
