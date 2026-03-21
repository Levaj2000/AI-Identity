"""Add human-readable run_id column to qa_runs.

Adds a date-based identifier (e.g. QA-20260321-003) as the public-facing
ID for QA runs. Backfills existing rows from their created_at timestamps.

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-03-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "h8c9d0e1f2g3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add column as nullable first (so existing rows don't block)
    op.add_column("qa_runs", sa.Column("run_id", sa.String(20), nullable=True))

    # 2. Backfill existing rows with date-based IDs derived from created_at
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, created_at FROM qa_runs ORDER BY created_at, id")
    ).fetchall()

    # Track per-day counters for sequential numbering
    day_counts: dict[str, int] = {}
    for row in rows:
        date_str = row.created_at.strftime("%Y%m%d")
        day_counts[date_str] = day_counts.get(date_str, 0) + 1
        run_id = f"QA-{date_str}-{day_counts[date_str]:03d}"
        conn.execute(
            sa.text("UPDATE qa_runs SET run_id = :run_id WHERE id = :id"),
            {"run_id": run_id, "id": row.id},
        )

    # 3. Make non-nullable and add unique index
    op.alter_column("qa_runs", "run_id", nullable=False)
    op.create_unique_constraint("uq_qa_runs_run_id", "qa_runs", ["run_id"])
    op.create_index("ix_qa_runs_run_id", "qa_runs", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_qa_runs_run_id", table_name="qa_runs")
    op.drop_constraint("uq_qa_runs_run_id", "qa_runs", type_="unique")
    op.drop_column("qa_runs", "run_id")
