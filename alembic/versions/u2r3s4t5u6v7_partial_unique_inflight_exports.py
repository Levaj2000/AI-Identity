"""Replace full unique constraint with partial unique index on in-flight.

Fixes the idempotency bug introduced in t1q2r3s4t5u6. The original
``uq_compliance_export_inflight`` was a UniqueConstraint that
included ``status`` in its column set — meaning only ONE failed row
could exist per scope, which broke every subsequent transition to
failed (cancel, orphan reap, re-attempt after signer misconfig).

This migration drops that constraint and replaces it with a partial
unique index that only enforces idempotency while the job is still
in-flight (``status IN ('queued', 'building')``). Terminal rows
(ready, failed) can accumulate without conflict, which is the
behavior the router always intended.

The constraint and the new index share the same name on purpose —
client code that references the constraint name by string keeps
working. The old name lives on the new partial index.

Revision ID: u2r3s4t5u6v7
Revises: t1q2r3s4t5u6
Create Date: 2026-04-23
"""

import sqlalchemy as sa

from alembic import op

revision = "u2r3s4t5u6v7"
down_revision = "t1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old full-column unique constraint. It exists in prod
    # (created by t1q2r3s4t5u6) but may be absent in sqlite test DBs
    # that were created via metadata.create_all after this migration
    # — guard with IF EXISTS where the dialect supports it.
    op.drop_constraint(
        "uq_compliance_export_inflight",
        "compliance_exports",
        type_="unique",
    )
    # Partial unique index: idempotency only while in-flight.
    op.create_index(
        "uq_compliance_export_inflight",
        "compliance_exports",
        [
            "org_id",
            "profile",
            "audit_period_start",
            "audit_period_end",
            "agent_ids_hash",
        ],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'building')"),
    )


def downgrade() -> None:
    op.drop_index("uq_compliance_export_inflight", table_name="compliance_exports")
    op.create_unique_constraint(
        "uq_compliance_export_inflight",
        "compliance_exports",
        [
            "org_id",
            "profile",
            "audit_period_start",
            "audit_period_end",
            "agent_ids_hash",
            "status",
        ],
    )
