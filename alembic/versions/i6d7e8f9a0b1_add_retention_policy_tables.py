"""add forensic retention policy tables (v0.5.0 Enterprise Forensics)

Revision ID: i6d7e8f9a0b1
Revises: h5c6d7e8f9a0
Create Date: 2026-09-14

Creates the three tables behind the forensic retention policy plane
(design: Notion "Forensic Retention Policies — Policy Model (v0.5.0)"):

* retention_policies — one row per immutable policy version. Exactly one
  active version per org (partial unique index).
* legal_holds — queryable current state of litigation/regulatory holds.
  Holds are ceiling-exempt: they freeze pruning past plan ceilings.
* retention_events — the retention_event record class: tombstones,
  redaction receipts, hold events, and policy publications. Exempt from
  ordinary retention rules; retained indefinitely.

Raw SQL with IF NOT EXISTS, following the repo convention — production
runs Base.metadata.create_all() at app startup, which may have already
created these tables before this migration runs.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "i6d7e8f9a0b1"
down_revision = "h5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_policies (
            id UUID NOT NULL,
            policy_id VARCHAR(64) NOT NULL,
            org_id UUID NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(16) NOT NULL DEFAULT 'draft',
            rules JSONB NOT NULL DEFAULT '[]',
            default_rule JSONB NOT NULL DEFAULT '{}',
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            effective_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            supersedes UUID,
            change_reason TEXT,
            approvals JSONB NOT NULL DEFAULT '[]',
            PRIMARY KEY (id),
            FOREIGN KEY(org_id) REFERENCES organizations (id) ON DELETE CASCADE,
            FOREIGN KEY(supersedes) REFERENCES retention_policies (id) ON DELETE SET NULL,
            UNIQUE (org_id, policy_id, version)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_retention_policies_org_id "
        "ON retention_policies (org_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_retention_policies_org_status "
        "ON retention_policies (org_id, status)"
    )
    # Exactly one active policy version per org.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_retention_policies_org_active "
        "ON retention_policies (org_id) WHERE status = 'active'"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS legal_holds (
            id UUID NOT NULL,
            org_id UUID NOT NULL,
            selector JSONB NOT NULL DEFAULT '{}',
            status VARCHAR(16) NOT NULL DEFAULT 'active',
            placed_by VARCHAR(255) NOT NULL,
            placed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            released_at TIMESTAMP WITH TIME ZONE,
            released_by VARCHAR(255),
            release_reason TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY(org_id) REFERENCES organizations (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_legal_holds_org_id "
        "ON legal_holds (org_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_legal_holds_org_status "
        "ON legal_holds (org_id, status)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_events (
            id UUID NOT NULL,
            org_id UUID NOT NULL,
            event_type VARCHAR(32) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}',
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(org_id) REFERENCES organizations (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_retention_events_org_id "
        "ON retention_events (org_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_retention_events_org_type_created "
        "ON retention_events (org_id, event_type, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_retention_events_org_created "
        "ON retention_events (org_id, created_at)"
    )
