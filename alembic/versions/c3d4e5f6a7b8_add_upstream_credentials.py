"""Add upstream_credentials table for Fernet-encrypted upstream API keys.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-12

Stores Fernet-encrypted upstream API credentials (OpenAI, Anthropic, etc.)
scoped to agents. The encrypted_key column contains only ciphertext —
plaintext keys are never persisted.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create upstream_credentials table with Fernet-encrypted key storage."""
    op.create_table(
        "upstream_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "agent_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_upstream_credentials_agent_id",
        "upstream_credentials",
        ["agent_id"],
    )
    op.create_index(
        "ix_upstream_credentials_provider",
        "upstream_credentials",
        ["provider"],
    )


def downgrade() -> None:
    """Drop upstream_credentials table."""
    op.drop_index(
        "ix_upstream_credentials_provider",
        table_name="upstream_credentials",
    )
    op.drop_index(
        "ix_upstream_credentials_agent_id",
        table_name="upstream_credentials",
    )
    op.drop_table("upstream_credentials")
