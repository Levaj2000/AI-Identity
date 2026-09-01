"""add epoch to edge audit events

Revision ID: h5c6d7e8f9a0
Revises: g4b5c6d7e8f9
Create Date: 2026-09-01 01:45:00.000000

The emitter documents stream_seq as dense within (epoch, stream_id) —
never across epochs, because a producer restart opens a new epoch and
legitimately resets the counter. Ingest was epoch-blind: it kept stream
tails per stream_id alone, so the first record after every restart was
flagged with a false "stream_seq gap" anomaly. Storing the epoch lets
continuity checks scope correctly and lets the streams read API group
segments the way the producer defined them.

Rows ingested before this migration keep NULL — their epoch is still
inside event."unmapped"."cpex.stream" if a backfill is ever wanted.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "h5c6d7e8f9a0"
down_revision = "g4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    # Use raw SQL with IF NOT EXISTS for idempotent migration —
    # production runs Base.metadata.create_all() at app startup, which
    # may have already added the column before this migration runs.
    op.execute("ALTER TABLE edge_audit_events ADD COLUMN IF NOT EXISTS epoch BIGINT")
    # The streams read surface groups by (edge, stream, epoch) and walks
    # seq ranges within each segment.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_events_edge_stream_epoch "
        "ON edge_audit_events (edge_id, stream_id, epoch, stream_seq)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_edge_events_edge_stream_epoch")
    op.execute("ALTER TABLE edge_audit_events DROP COLUMN IF EXISTS epoch")
