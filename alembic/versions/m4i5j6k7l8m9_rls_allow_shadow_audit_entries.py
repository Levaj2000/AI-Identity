"""Update audit_log RLS to allow shadow agent denied entries.

Shadow agent denied entries have user_id = NULL and an agent_id that
doesn't exist in the agents table. The previous RLS policy made these
rows invisible to all non-service queries. This migration adds a clause
to allow denied entries with NULL user_id to be visible, since they
contain no sensitive data and are needed for shadow agent investigation
in the Forensics page.

Revision ID: m4i5j6k7l8m9
Revises: l3h4i5j6k7l8
Create Date: 2026-04-03
"""

from alembic import op

revision = "m4i5j6k7l8m9"
down_revision = "l3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    # Drop and recreate the tenant_isolation policy on audit_log
    # to include shadow agent denied entries (user_id IS NULL, decision = 'deny')
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audit_log")
    op.execute(
        "CREATE POLICY tenant_isolation ON audit_log FOR ALL "
        "USING ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR agent_id IN (SELECT id FROM agents WHERE org_id = current_setting('app.current_org_id', true)::uuid)"
        "  OR (user_id IS NULL AND decision = 'deny')"
        ") "
        "WITH CHECK ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR agent_id IN (SELECT id FROM agents WHERE org_id = current_setting('app.current_org_id', true)::uuid)"
        ")"
    )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    # Restore original policy without shadow agent clause
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audit_log")
    op.execute(
        "CREATE POLICY tenant_isolation ON audit_log FOR ALL "
        "USING ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR agent_id IN (SELECT id FROM agents WHERE org_id = current_setting('app.current_org_id', true)::uuid)"
        ") "
        "WITH CHECK ("
        "  user_id = current_setting('app.current_user_id', true)::uuid "
        "  OR agent_id IN (SELECT id FROM agents WHERE org_id = current_setting('app.current_org_id', true)::uuid)"
        ")"
    )
