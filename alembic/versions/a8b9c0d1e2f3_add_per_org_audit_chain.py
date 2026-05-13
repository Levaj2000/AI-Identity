"""Add per-org audit chain columns.

Phase 1 of the per-org audit chain migration. Adds three nullable columns
to audit_log so the writer can populate them in dual-write mode without
breaking existing rows. Phase 2 backfills legacy rows; Phase 3 cuts the
verifier over to the per-org chain.

  prev_hash_org   — HMAC of the previous row written by *this* org
                    (GENESIS for an org's first row)
  entry_hash_org  — HMAC of this row computed against prev_hash_org
  org_chain_seq   — 1-based monotonic sequence within org_id; the
                    completeness guard. Backed by a partial UNIQUE
                    index so the constraint kicks in only on rows the
                    writer has populated.

See docs/audit-chain-per-org-migration.md for the full plan.

Revision ID: a8b9c0d1e2f3
Revises: z7a8b9c0d1e2
Create Date: 2026-05-13
"""

import sqlalchemy as sa
from alembic import op

revision = "a8b9c0d1e2f3"
down_revision = "z7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All three columns are nullable in Phase 1 — the writer populates
    # them on new rows when the dual-write flag is on, and the Phase 2
    # backfill fills them on legacy rows. They become NOT NULL after
    # backfill completes.
    op.execute(
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS prev_hash_org VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS entry_hash_org VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS org_chain_seq BIGINT"
    )

    # UNIQUE on (org_id, org_chain_seq) — completeness guard. NULLs are
    # distinct under SQL's default behavior, so legacy unbackfilled rows
    # don't collide; populated rows enforce one-row-per-sequence per org.
    # Belt-and-suspenders against any advisory-lock bug: a duplicate
    # sequence number fails the insert outright.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_log_org_chain_seq "
        "ON audit_log (org_id, org_chain_seq)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_audit_log_org_chain_seq")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS org_chain_seq")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS entry_hash_org")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS prev_hash_org")
