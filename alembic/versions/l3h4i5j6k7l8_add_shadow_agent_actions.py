"""Add blocked_agents and dismissed_shadow_agents tables.

Supports shadow agent action flows: block (gateway enforcement),
dismiss (UI hide), and the data backing for both.

Revision ID: l3h4i5j6k7l8
Revises: k2g3h4i5j6k7
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "l3h4i5j6k7l8"
down_revision = "k2g3h4i5j6k7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── blocked_agents ──────────────────────────────────────────────
    op.create_table(
        "blocked_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "agent_id", name="uq_blocked_user_agent"),
    )
    op.create_index("ix_blocked_agents_agent_id", "blocked_agents", ["agent_id"])
    op.create_index("ix_blocked_agents_user_id", "blocked_agents", ["user_id"])

    # ── dismissed_shadow_agents ─────────────────────────────────────
    op.create_table(
        "dismissed_shadow_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "agent_id", name="uq_dismissed_user_agent"),
    )
    op.create_index("ix_dismissed_shadow_user_id", "dismissed_shadow_agents", ["user_id"])

    # ── RLS (PostgreSQL only) ───────────────────────────────────────
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        for table in ("blocked_agents", "dismissed_shadow_agents"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

            # Tenant isolation: users see only their own rows
            op.execute(
                f"CREATE POLICY tenant_isolation ON {table} FOR ALL "
                f"USING (user_id = current_setting('app.current_user_id', true)::uuid) "
                f"WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)"
            )

            # Service bypass: gateway and background jobs run without user context
            op.execute(
                f"CREATE POLICY service_bypass ON {table} FOR ALL "
                f"USING (current_setting('app.is_service', true) = 'true') "
                f"WITH CHECK (current_setting('app.is_service', true) = 'true')"
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        for table in ("dismissed_shadow_agents", "blocked_agents"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
            op.execute(f"DROP POLICY IF EXISTS service_bypass ON {table}")

    op.drop_table("dismissed_shadow_agents")
    op.drop_table("blocked_agents")
