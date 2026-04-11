"""Add per-org forensic_verify_key for audit chain verification.

Each organization gets a unique HMAC signing key so customers can verify
their own audit exports without sharing a global secret.

Revision ID: n5j6k7l8m9n0
Revises: m4i5j6k7l8m9
Create Date: 2026-04-10
"""

import secrets

import sqlalchemy as sa
from alembic import op

revision = "n5j6k7l8m9n0"
down_revision = "m4i5j6k7l8m9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add the column as nullable first so we can backfill
    op.add_column(
        "organizations",
        sa.Column("forensic_verify_key", sa.String(64), nullable=True, unique=False),
    )

    # 2. Add unique constraint (deferred — backfill will populate unique values)
    op.create_unique_constraint(
        "uq_organizations_forensic_verify_key",
        "organizations",
        ["forensic_verify_key"],
    )

    # 3. Backfill: assign a unique key to every existing org
    bind = op.get_bind()
    orgs = bind.execute(sa.text("SELECT id FROM organizations WHERE forensic_verify_key IS NULL"))
    for row in orgs.fetchall():
        org_id = row[0]
        key = secrets.token_hex(32)
        bind.execute(
            sa.text(
                "UPDATE organizations SET forensic_verify_key = :key WHERE id = :id"
            ),
            {"key": key, "id": str(org_id)},
        )


def downgrade() -> None:
    op.drop_constraint("uq_organizations_forensic_verify_key", "organizations", type_="unique")
    op.drop_column("organizations", "forensic_verify_key")
