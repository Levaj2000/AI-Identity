"""add edge deployments and edge audit events

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-08-22 17:30:00.000000

Component A of docs/specs/praxis-edge-enforcement.md: registered edge
enforcement points and their arrival-verified OCSF records.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "g4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade():
    # Use raw SQL with IF NOT EXISTS for idempotent migration —
    # production runs Base.metadata.create_all() at app startup, which
    # may have already created the tables before this migration runs.
    op.execute("""
        CREATE TABLE IF NOT EXISTS edge_deployments (
            id UUID NOT NULL,
            org_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            chain_uid VARCHAR(255) NOT NULL,
            authority_uid VARCHAR(255),
            verify_key_pem TEXT NOT NULL,
            key_id VARCHAR(255),
            ingest_key_hash VARCHAR(64) NOT NULL,
            ingest_key_prefix VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            last_ingest_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id),
            FOREIGN KEY(org_id) REFERENCES organizations (id) ON DELETE CASCADE,
            UNIQUE (chain_uid),
            UNIQUE (ingest_key_hash)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_deployments_org_id ON edge_deployments (org_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_deployments_chain_uid "
        "ON edge_deployments (chain_uid)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_deployments_ingest_key_hash "
        "ON edge_deployments (ingest_key_hash)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS edge_audit_events (
            id SERIAL NOT NULL,
            org_id UUID NOT NULL,
            edge_id UUID NOT NULL,
            chain_uid VARCHAR(255),
            metadata_uid VARCHAR(128),
            dedupe_key VARCHAR(255),
            fingerprint VARCHAR(64),
            stream_id VARCHAR(255),
            stream_seq BIGINT,
            emission_seq BIGINT,
            chain_position BIGINT,
            verification_status VARCHAR(20) NOT NULL,
            failure_reason TEXT,
            anomalies TEXT,
            event JSONB NOT NULL,
            received_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(edge_id) REFERENCES edge_deployments (id) ON DELETE CASCADE,
            CONSTRAINT uq_edge_events_dedupe UNIQUE (edge_id, dedupe_key)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_audit_events_org_id ON edge_audit_events (org_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_audit_events_edge_id ON edge_audit_events (edge_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_events_edge_chain_id "
        "ON edge_audit_events (edge_id, chain_uid, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_edge_events_org_received "
        "ON edge_audit_events (org_id, received_at)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_edge_events_org_received")
    op.execute("DROP INDEX IF EXISTS ix_edge_events_edge_chain_id")
    op.execute("DROP INDEX IF EXISTS ix_edge_audit_events_edge_id")
    op.execute("DROP INDEX IF EXISTS ix_edge_audit_events_org_id")
    op.execute("DROP TABLE IF EXISTS edge_audit_events")
    op.execute("DROP INDEX IF EXISTS ix_edge_deployments_ingest_key_hash")
    op.execute("DROP INDEX IF EXISTS ix_edge_deployments_chain_uid")
    op.execute("DROP INDEX IF EXISTS ix_edge_deployments_org_id")
    op.execute("DROP TABLE IF EXISTS edge_deployments")
