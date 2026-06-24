"""Add (org_id, id) index on audit_log for the Evidence Anchor checkpoint cron.

#408 follow-on. The checkpoint cron's candidate query groups audit_log by
org_id and takes max(id) to find the orgs whose audit_log is ahead of their
checkpoint high-water mark — i.e. the orgs that actually have un-anchored rows.
Without a (org_id, id) index Postgres does a full seq scan + hash aggregate of
audit_log on every tick; this B-tree lets it satisfy the grouped-max with an
index scan instead. (No loose/skip index scan is needed — an ordinary ordered
index scan over (org_id, id) yields the per-group max.)

Additive, non-destructive index. On a very large audit_log this build briefly
locks writes; create it CONCURRENTLY out-of-band first in production if that
window is unacceptable, then stamp this revision.

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-22
"""

from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_log_org_id_id",
        "audit_log",
        ["org_id", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_org_id_id", table_name="audit_log")
