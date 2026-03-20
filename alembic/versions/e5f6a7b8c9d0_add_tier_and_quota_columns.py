"""Add tier and quota columns to users table.

Adds subscription tier (free/pro/enterprise) and monthly request
tracking fields to support per-tier quota enforcement.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tier column with default 'free' for existing users
    op.add_column(
        "users",
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
    )
    op.create_index("ix_users_tier", "users", ["tier"])

    # Add monthly request counter
    op.add_column(
        "users",
        sa.Column("requests_this_month", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add usage reset day (day of month)
    op.add_column(
        "users",
        sa.Column("usage_reset_day", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_tier", table_name="users")
    op.drop_column("users", "usage_reset_day")
    op.drop_column("users", "requests_this_month")
    op.drop_column("users", "tier")
