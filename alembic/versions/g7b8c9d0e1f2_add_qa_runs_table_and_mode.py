"""Add qa_runs table and mode column.

Creates the qa_runs table for QA checklist persistence and sign-off
tracking. Adds the 'mode' column to distinguish admin checks from
client onboarding simulations.

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-20 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "g7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create qa_runs table if it doesn't exist
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'qa_runs')")
    )
    table_exists = result.scalar()

    if not table_exists:
        op.create_table(
            "qa_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="passed"),
            sa.Column("run_by", sa.String(255), nullable=False),
            sa.Column("environment", sa.String(50), nullable=False, server_default="production"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mode", sa.String(20), nullable=True, server_default="admin"),
            sa.Column("results", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("customer_signoff_by", sa.String(255), nullable=True),
            sa.Column("customer_signoff_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("customer_signoff_note", sa.Text(), nullable=True),
            sa.Column("staff_signoff_by", sa.String(255), nullable=True),
            sa.Column("staff_signoff_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("staff_signoff_note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        # Table exists — add mode column if missing
        result = conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.columns "
                "  WHERE table_name = 'qa_runs' AND column_name = 'mode'"
                ")"
            )
        )
        if not result.scalar():
            op.add_column(
                "qa_runs",
                sa.Column("mode", sa.String(20), nullable=True, server_default="admin"),
            )
            # Backfill existing rows
            op.execute("UPDATE qa_runs SET mode = 'admin' WHERE mode IS NULL")


def downgrade() -> None:
    # Only drop the mode column, not the whole table, to preserve data
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'qa_runs' AND column_name = 'mode'"
            ")"
        )
    )
    if result.scalar():
        op.drop_column("qa_runs", "mode")
