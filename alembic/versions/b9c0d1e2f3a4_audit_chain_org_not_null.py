"""Flip per-org audit chain columns to NOT NULL.

┌─ Operator pre-flight (DATA-DEPENDENT MIGRATION) ──────────────────┐
│ This migration's upgrade() refuses to apply if any audit_log row  │
│ has NULL per-org chain columns. Before merging the PR carrying    │
│ this migration:                                                   │
│   1. python scripts/backfill_per_org_chain.py                     │
│   2. python scripts/verify_per_org_chain.py     # must exit 0     │
│ Both run safely against prod (idempotent, advisory-lock-guarded). │
│                                                                   │
│ Why the guard: see docs/audit-chain-per-org-migration.md          │
│ "Lessons Learned" — bundling a data-dependent migration with the  │
│ script that prepares its data caused a deploy retry loop during   │
│ the original Phase 2b roll-out (2026-05-13). The convention now   │
│ is: prep data → verify → open the migration PR.                   │
└───────────────────────────────────────────────────────────────────┘

Phase 2 finisher. Runs AFTER scripts/backfill_per_org_chain.py and
scripts/verify_per_org_chain.py have confirmed every row is populated
and every chain is intact. The upgrade asserts zero NULL rows before
altering — if backfill hasn't completed, the migration aborts loudly
rather than silently leaving the columns nullable.

The downgrade restores nullability so a Phase 1 rollback is still
possible (dual-write can be flipped off, leaving new rows with NULLs).

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-05-13
"""

from alembic import op
from sqlalchemy import text

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gate: refuse to flip NOT NULL if any row still has NULLs.
    bind = op.get_bind()
    null_count = bind.execute(
        text(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE prev_hash_org IS NULL "
            "OR entry_hash_org IS NULL "
            "OR org_chain_seq IS NULL"
        )
    ).scalar_one()
    if null_count and null_count > 0:
        raise RuntimeError(
            f"audit_log has {null_count} rows with NULL per-org chain columns. "
            "Run scripts/backfill_per_org_chain.py and "
            "scripts/verify_per_org_chain.py before upgrading."
        )

    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN prev_hash_org SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN entry_hash_org SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN org_chain_seq SET NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN org_chain_seq DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN entry_hash_org DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN prev_hash_org DROP NOT NULL"
    )
