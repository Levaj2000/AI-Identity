"""Add forensic_attestations for signed session-close evidence packets.

Milestone #33 (forensic attestations). One row per successful sign —
the authoritative envelope lives in the JSONB column; mirrored columns
exist for indexing. Unique constraint on (org_id, session_id) enforces
idempotent re-signs: the router should return the existing row on
duplicate POST rather than create a conflicting attestation.

Revision ID: r9o0p1q2r3s4
Revises: q8n9o0p1q2r3
Create Date: 2026-04-17
"""

import sqlalchemy as sa

from alembic import op

revision = "r9o0p1q2r3s4"
down_revision = "q8n9o0p1q2r3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forensic_attestations",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("first_audit_id", sa.Integer(), nullable=False),
        sa.Column("last_audit_id", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        # Purge-resilience: store the resolved audit_log row IDs so a
        # verifier can detect "chain existed at sign time, N rows now
        # missing" instead of silently accepting a truncated range.
        sa.Column(
            "audit_log_ids",
            sa.dialects.postgresql.ARRAY(sa.Integer()),
            nullable=False,
        ),
        sa.Column(
            "session_start",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "session_end",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("signer_key_id", sa.String(512), nullable=False),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # The full DSSE envelope — the authoritative artifact. All the
        # mirrored columns above can be derived from it; they exist
        # only so common queries don't need to JSONB-traverse.
        sa.Column(
            "envelope",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "session_id", name="uq_attestation_org_session"),
    )

    op.create_index(
        "ix_forensic_attestation_org_id",
        "forensic_attestations",
        ["org_id"],
    )
    op.create_index(
        "ix_forensic_attestation_session_id",
        "forensic_attestations",
        ["session_id"],
    )
    op.create_index(
        "ix_forensic_attestation_range",
        "forensic_attestations",
        ["org_id", "first_audit_id", "last_audit_id"],
    )
    op.create_index(
        "ix_forensic_attestation_signed_at",
        "forensic_attestations",
        ["org_id", "signed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_forensic_attestation_signed_at",
        table_name="forensic_attestations",
    )
    op.drop_index(
        "ix_forensic_attestation_range",
        table_name="forensic_attestations",
    )
    op.drop_index(
        "ix_forensic_attestation_session_id",
        table_name="forensic_attestations",
    )
    op.drop_index(
        "ix_forensic_attestation_org_id",
        table_name="forensic_attestations",
    )
    op.drop_table("forensic_attestations")
