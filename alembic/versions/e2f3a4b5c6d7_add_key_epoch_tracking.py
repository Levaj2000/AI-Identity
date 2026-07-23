"""Add key-epoch tracking: audit_log.key_fingerprint + organizations.forensic_key_history.

Orgs get their forensic_verify_key lazily (first dashboard view of the
Forensics page) and can regenerate it, so one org's audit chain can span
several HMAC key epochs. Before this change nothing recorded WHICH key a
row was hashed under, so a customer verifying an export that crosses an
epoch boundary saw "CHAIN BROKEN / hash mismatch" — indistinguishable
from tampering.

Two additive columns fix this without touching a single stored hash
(the audit_log_no_update trigger stays honest):

* ``audit_log.key_fingerprint`` — SHA-256[:16] of the HMAC key used for
  the row's hashes, stamped at write time. Derived metadata; NOT part of
  the hashed payload. Legacy rows are stamped by
  scripts/backfill_key_fingerprints.py.
* ``organizations.forensic_key_history`` — retired keys (JSONB list),
  appended on regeneration so earlier epochs stay verifiable.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column(
            "key_fingerprint",
            sa.String(16),
            nullable=True,
            comment="SHA-256[:16] fingerprint of the HMAC key used for this row's hashes",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("forensic_key_history", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "forensic_key_history")
    op.drop_column("audit_log", "key_fingerprint")
