"""Add org_id to audit_log — first-class tenant on every event.

Enables fast org-scoped queries for enterprise log extraction (Cisco-scale:
100+ agents, multi-user orgs, SIEM feeds) and unblocks the fix for the
system-wide admin leak in GET /api/v1/audit/admin.

Backfill strategy:
1. Create a sentinel "__system__" user and org (fixed UUIDs) as the tenant
   for orphan audit rows — shadow agents, pre-auth errors, etc.
2. For every user with a NULL org_id, create a "Personal workspace (xxxx)"
   org (xxxx = first 4 hex chars of user.id), make them the owner, add an
   OrgMembership(role=owner), and set users.org_id to the new org.
3. For every agent with a NULL org_id, copy its owner's org_id.
4. Add audit_log.org_id nullable, populate from agent.org_id, route any
   remaining NULLs to the system org, then SET NOT NULL + index.

org_id is deliberately NOT added to the HMAC canonical payload — it's a
derived access-control field (same treatment as user_id and agent_name).
Existing HMAC chains remain valid after backfill.

Revision ID: o6l7m8n9o0p1
Revises: n5j6k7l8m9n0
Create Date: 2026-04-15
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "o6l7m8n9o0p1"
down_revision = "n5j6k7l8m9n0"
branch_labels = None
depends_on = None

# Sentinel IDs — kept in sync with common/models/organization.py
SYSTEM_USER_ID = "ffffffff-ffff-ffff-ffff-fffffffffffe"
SYSTEM_ORG_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
SYSTEM_USER_EMAIL = "__system__@ai-identity.internal"
SYSTEM_ORG_NAME = "__system__"


def upgrade() -> None:
    """Backfill org_id across users/agents/audit_log and enforce NOT NULL."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ── 1. Ensure the sentinel system user + org exist ─────────────
    # Check first so re-running the migration on a partially-applied DB
    # doesn't fail on PK conflicts.
    existing_sys_user = bind.execute(
        sa.text("SELECT 1 FROM users WHERE id = :id"), {"id": SYSTEM_USER_ID}
    ).first()
    if existing_sys_user is None:
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, role, tier) "
                "VALUES (:id, :email, 'system', 'enterprise')"
            ),
            {"id": SYSTEM_USER_ID, "email": SYSTEM_USER_EMAIL},
        )

    existing_sys_org = bind.execute(
        sa.text("SELECT 1 FROM organizations WHERE id = :id"), {"id": SYSTEM_ORG_ID}
    ).first()
    if existing_sys_org is None:
        bind.execute(
            sa.text(
                "INSERT INTO organizations (id, name, owner_id, tier, requests_this_month, usage_reset_day) "
                "VALUES (:id, :name, :owner, 'enterprise', 0, 1)"
            ),
            {"id": SYSTEM_ORG_ID, "name": SYSTEM_ORG_NAME, "owner": SYSTEM_USER_ID},
        )

    # ── 2. Personal org for every org-less real user ───────────────
    # Skip the system user itself (it owns the system org, not a personal one).
    orgless_users = bind.execute(
        sa.text(
            "SELECT id FROM users WHERE org_id IS NULL AND id != :sys_id"
        ),
        {"sys_id": SYSTEM_USER_ID},
    ).fetchall()

    for (user_id,) in orgless_users:
        user_id_str = str(user_id)
        # First 4 hex chars of the user UUID, no hyphens
        suffix = user_id_str.replace("-", "")[:4]
        org_name = f"Personal workspace ({suffix})"
        new_org_id = str(uuid.uuid4())

        bind.execute(
            sa.text(
                "INSERT INTO organizations (id, name, owner_id, tier, requests_this_month, usage_reset_day) "
                "VALUES (:id, :name, :owner, 'free', 0, 1)"
            ),
            {"id": new_org_id, "name": org_name, "owner": user_id_str},
        )
        bind.execute(
            sa.text(
                "INSERT INTO org_memberships (id, org_id, user_id, role) "
                "VALUES (:mid, :oid, :uid, 'owner')"
            ),
            {"mid": str(uuid.uuid4()), "oid": new_org_id, "uid": user_id_str},
        )
        bind.execute(
            sa.text("UPDATE users SET org_id = :oid WHERE id = :uid"),
            {"oid": new_org_id, "uid": user_id_str},
        )

    # ── 3. Backfill agent.org_id from its owner ────────────────────
    # Only covers real agents owned by users who now have an org.
    if dialect == "postgresql":
        op.execute(
            "UPDATE agents SET org_id = users.org_id "
            "FROM users "
            "WHERE agents.user_id = users.id "
            "  AND agents.org_id IS NULL "
            "  AND users.org_id IS NOT NULL"
        )
    else:
        # SQLite UPDATE...FROM syntax differs; use correlated subquery.
        op.execute(
            "UPDATE agents SET org_id = ("
            "  SELECT org_id FROM users WHERE users.id = agents.user_id"
            ") WHERE org_id IS NULL"
        )

    # ── 4. Add audit_log.org_id nullable for backfill ──────────────
    op.add_column("audit_log", sa.Column("org_id", sa.UUID(), nullable=True))

    # ── 5. Backfill audit_log.org_id from agent.org_id ─────────────
    if dialect == "postgresql":
        op.execute(
            "UPDATE audit_log SET org_id = agents.org_id "
            "FROM agents "
            "WHERE audit_log.agent_id = agents.id "
            "  AND audit_log.org_id IS NULL "
            "  AND agents.org_id IS NOT NULL"
        )
    else:
        op.execute(
            "UPDATE audit_log SET org_id = ("
            "  SELECT org_id FROM agents WHERE agents.id = audit_log.agent_id"
            ") WHERE org_id IS NULL"
        )

    # ── 6. Any remaining NULLs (orphan/shadow) → system org ────────
    op.execute(
        f"UPDATE audit_log SET org_id = '{SYSTEM_ORG_ID}' WHERE org_id IS NULL"
    )

    # ── 7. Enforce NOT NULL + add FK + index ───────────────────────
    op.alter_column("audit_log", "org_id", nullable=False)
    op.create_foreign_key(
        "fk_audit_log_org_id",
        "audit_log",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_audit_log_org_created", "audit_log", ["org_id", "created_at"])


def downgrade() -> None:
    """Reverse: drop the org_id column and index.

    NOTE: This does NOT reverse the personal-org or system-org creation.
    Those records are safe to keep; dropping them would leave users and
    agents with dangling FKs (org_id on users/agents was already nullable).
    """
    op.drop_index("ix_audit_log_org_created", table_name="audit_log")
    op.drop_constraint("fk_audit_log_org_id", "audit_log", type_="foreignkey")
    op.drop_column("audit_log", "org_id")
