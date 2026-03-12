"""Add key_type column to agent_keys for runtime vs admin key separation.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-11

Adds key_type column (runtime|admin) to differentiate between agent runtime
keys (aid_sk_) and management keys (aid_admin_). Existing keys default to
'runtime' for backward compatibility.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add key_type column with default 'runtime' for backward compatibility."""
    op.add_column(
        "agent_keys",
        sa.Column(
            "key_type",
            sa.String(20),
            nullable=False,
            server_default="runtime",
        ),
    )

    # Create index for efficient key-type filtering
    op.create_index(
        "ix_agent_keys_key_type",
        "agent_keys",
        ["key_type"],
    )


def downgrade() -> None:
    """Remove key_type column."""
    op.drop_index("ix_agent_keys_key_type", table_name="agent_keys")
    op.drop_column("agent_keys", "key_type")
