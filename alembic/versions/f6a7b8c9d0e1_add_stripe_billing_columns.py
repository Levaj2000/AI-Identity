"""Add Stripe billing columns to users table.

Adds stripe_customer_id and stripe_subscription_id for linking
user accounts to Stripe billing.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-18 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, unique=True),
    )
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"])

    op.add_column(
        "users",
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, unique=True),
    )
    op.create_index("ix_users_stripe_subscription_id", "users", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_users_stripe_subscription_id", table_name="users")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "stripe_customer_id")
