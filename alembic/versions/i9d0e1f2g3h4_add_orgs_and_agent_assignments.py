"""Add organizations, org memberships, and agent assignments.

Creates the organization, org_membership, and agent_assignment tables.
Migrates users.org_id from String to UUID FK. Adds org_id FK to agents.
Updates RLS tenant_isolation policies to include org-based access.

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "i9d0e1f2g3h4"
down_revision = "h8c9d0e1f2g3"
branch_labels = None
depends_on = None

# Tables that have tenant_isolation policies to update
RLS_DIRECT_TABLES = ["agents"]
RLS_INDIRECT_TABLES = ["agent_keys", "policies", "upstream_credentials"]
RLS_AUDIT_TABLE = "audit_log"
ALL_RLS_TABLES = RLS_DIRECT_TABLES + RLS_INDIRECT_TABLES + [RLS_AUDIT_TABLE]


def upgrade() -> None:
    """Create org tables, migrate user.org_id, add agent.org_id, update RLS."""
    dialect = op.get_bind().dialect.name

    # ── 1. Create organizations table ─────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("requests_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_reset_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )

    # ── 2. Create org_memberships table ───────────────────────────────
    op.create_table(
        "org_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_membership"),
    )
    op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])

    # ── 3. Create agent_assignments table ─────────────────────────────
    op.create_table(
        "agent_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_id", "user_id", name="uq_agent_assignment"),
    )
    op.create_index("ix_agent_assignments_agent_id", "agent_assignments", ["agent_id"])
    op.create_index("ix_agent_assignments_user_id", "agent_assignments", ["user_id"])

    # ── 4. Migrate users.org_id from String to UUID FK ────────────────
    # Drop the old String column and add a new UUID FK column
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "org_id")
    op.add_column("users", sa.Column("org_id", sa.UUID(), nullable=True))
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_foreign_key(
        "fk_users_org_id", "users", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )

    # ── 5. Add org_id FK to agents ────────────────────────────────────
    op.add_column("agents", sa.Column("org_id", sa.UUID(), nullable=True))
    op.create_index("ix_agents_org_id", "agents", ["org_id"])
    op.create_foreign_key(
        "fk_agents_org_id", "agents", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )

    # ── 6. Update RLS policies (PostgreSQL only) ──────────────────────
    if dialect != "postgresql":
        return

    # Drop existing tenant_isolation policies on all 5 tables
    for table in ALL_RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    # Recreate tenant_isolation on agents with org OR logic
    op.execute(
        "CREATE POLICY tenant_isolation ON agents FOR ALL "
        "USING ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR org_id = current_setting('app.current_org_id', true)::uuid"
        ") "
        "WITH CHECK ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR org_id = current_setting('app.current_org_id', true)::uuid"
        ")"
    )

    # Recreate tenant_isolation on audit_log with org OR logic
    op.execute(
        "CREATE POLICY tenant_isolation ON audit_log FOR ALL "
        "USING ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR agent_id IN (SELECT id FROM agents WHERE org_id = current_setting('app.current_org_id', true)::uuid)"
        ") "
        "WITH CHECK ("
        "  user_id = current_setting('app.current_user_id', true)::uuid"
        ")"
    )

    # Recreate tenant_isolation on indirect tables (agent_keys, policies, upstream_credentials)
    for table in RLS_INDIRECT_TABLES:
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL "
            f"USING ("
            f"  agent_id IN ("
            f"    SELECT id FROM agents "
            f"    WHERE user_id = current_setting('app.current_user_id', true)::uuid "
            f"       OR org_id = current_setting('app.current_org_id', true)::uuid"
            f"  )"
            f") "
            f"WITH CHECK ("
            f"  agent_id IN ("
            f"    SELECT id FROM agents "
            f"    WHERE user_id = current_setting('app.current_user_id', true)::uuid "
            f"       OR org_id = current_setting('app.current_org_id', true)::uuid"
            f"  )"
            f")"
        )


def downgrade() -> None:
    """Reverse: drop org tables, restore old user.org_id, remove agent.org_id, restore RLS."""
    dialect = op.get_bind().dialect.name

    # ── 6. Restore original RLS policies (PostgreSQL only) ────────────
    if dialect == "postgresql":
        # Drop the org-aware policies
        for table in ALL_RLS_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

        # Restore original direct user_id policies (agents, audit_log)
        for table in ["agents", "audit_log"]:
            op.execute(
                f"CREATE POLICY tenant_isolation ON {table} FOR ALL "
                f"USING (user_id = current_setting('app.current_user_id', true)::uuid) "
                f"WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)"
            )

        # Restore original indirect policies (agent_keys, policies, upstream_credentials)
        for table in RLS_INDIRECT_TABLES:
            op.execute(
                f"CREATE POLICY tenant_isolation ON {table} FOR ALL "
                f"USING (agent_id IN ("
                f"  SELECT id FROM agents "
                f"  WHERE user_id = current_setting('app.current_user_id', true)::uuid"
                f")) "
                f"WITH CHECK (agent_id IN ("
                f"  SELECT id FROM agents "
                f"  WHERE user_id = current_setting('app.current_user_id', true)::uuid"
                f"))"
            )

    # ── 5. Drop org_id from agents ────────────────────────────────────
    op.drop_constraint("fk_agents_org_id", "agents", type_="foreignkey")
    op.drop_index("ix_agents_org_id", table_name="agents")
    op.drop_column("agents", "org_id")

    # ── 4. Restore users.org_id as String column ──────────────────────
    op.drop_constraint("fk_users_org_id", "users", type_="foreignkey")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "org_id")
    op.add_column("users", sa.Column("org_id", sa.String(255), nullable=True))
    op.create_index("ix_users_org_id", "users", ["org_id"])

    # ── 3. Drop agent_assignments table ───────────────────────────────
    op.drop_index("ix_agent_assignments_user_id", table_name="agent_assignments")
    op.drop_index("ix_agent_assignments_agent_id", table_name="agent_assignments")
    op.drop_table("agent_assignments")

    # ── 2. Drop org_memberships table ─────────────────────────────────
    op.drop_index("ix_org_memberships_user_id", table_name="org_memberships")
    op.drop_index("ix_org_memberships_org_id", table_name="org_memberships")
    op.drop_table("org_memberships")

    # ── 1. Drop organizations table ──────────────────────────────────
    op.drop_table("organizations")
