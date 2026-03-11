"""Add HMAC integrity chain fields to audit_log + append-only triggers.

Revision ID: a1b2c3d4e5f6
Revises: 00fec4eb50ea
Create Date: 2026-03-11

Adds entry_hash and prev_hash columns for the HMAC integrity chain,
plus PostgreSQL triggers that prevent UPDATE/DELETE on audit_log
(append-only enforcement for SOC 2 compliance).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "00fec4eb50ea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add integrity chain columns and append-only triggers."""

    # 1. Add integrity chain columns (nullable initially for safety)
    op.add_column(
        "audit_log",
        sa.Column(
            "entry_hash",
            sa.String(64),
            nullable=True,
            comment="HMAC-SHA256 of this entry's canonical data + prev_hash",
        ),
    )
    op.add_column(
        "audit_log",
        sa.Column(
            "prev_hash",
            sa.String(64),
            nullable=True,
            comment="entry_hash of the preceding row; GENESIS for the first entry",
        ),
    )

    # 2. Index on entry_hash for fast chain lookups
    op.create_index("ix_audit_log_entry_hash", "audit_log", ["entry_hash"])

    # 3. Set NOT NULL — safe because the table is empty at migration time
    op.alter_column("audit_log", "entry_hash", nullable=False)
    op.alter_column("audit_log", "prev_hash", nullable=False)

    # 4. Append-only enforcement (PostgreSQL only — skip on SQLite for tests)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        # Trigger function that raises on UPDATE or DELETE
        conn.execute(
            text("""
                CREATE OR REPLACE FUNCTION audit_log_immutable()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_log is append-only: % not permitted', TG_OP;
                END;
                $$ LANGUAGE plpgsql;
            """)
        )

        # Block UPDATE
        conn.execute(
            text("""
                CREATE TRIGGER audit_log_no_update
                BEFORE UPDATE ON audit_log
                FOR EACH ROW
                EXECUTE FUNCTION audit_log_immutable();
            """)
        )

        # Block DELETE
        conn.execute(
            text("""
                CREATE TRIGGER audit_log_no_delete
                BEFORE DELETE ON audit_log
                FOR EACH ROW
                EXECUTE FUNCTION audit_log_immutable();
            """)
        )


def downgrade() -> None:
    """Remove integrity chain columns and append-only triggers."""
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(text("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;"))
        conn.execute(text("DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log;"))
        conn.execute(text("DROP FUNCTION IF EXISTS audit_log_immutable();"))

    op.drop_index("ix_audit_log_entry_hash", table_name="audit_log")
    op.drop_column("audit_log", "prev_hash")
    op.drop_column("audit_log", "entry_hash")
