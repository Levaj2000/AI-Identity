"""Add correlation_id to audit_log — end-to-end request tracing.

One UUID travels the full request: client → API → gateway → audit row.
This lets operators (and SIEM pipelines) reconstruct a single user
action across services with a point query, instead of guessing at
timestamps to stitch logs together.

Nullable because:
  * Legacy rows have no correlation ID to backfill (the data was never
    captured at write time — can't invent it).
  * Background jobs and migrations run outside an HTTP request; they
    legitimately have no correlation context.

The top-level column is denormalized from ``request_metadata.correlation_id``
for indexable cross-service lookups. Not part of the HMAC canonical
payload — it's operational metadata, not a statement about what the
request did. Existing chains verify unchanged.

Revision ID: p7m8n9o0p1q2
Revises: o6l7m8n9o0p1
Create Date: 2026-04-15
"""

import sqlalchemy as sa

from alembic import op

revision = "p7m8n9o0p1q2"
down_revision = "o6l7m8n9o0p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column("correlation_id", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_audit_log_correlation_id",
        "audit_log",
        ["correlation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_correlation_id", table_name="audit_log")
    op.drop_column("audit_log", "correlation_id")
