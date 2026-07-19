"""Shared user deletion utility — handles all FK relationships safely.

Used by both the one-time purge script and the automated cleanup cron.
Preserves audit_log rows (soft FK) and denormalizes agent_name before deletion.

Evidence retention: a user whose organization still holds audit_log rows is
never deleted. organizations.owner_id cascades on user delete, but
audit_log.org_id is the tamper-evident chain's partition key (NOT NULL,
fk_audit_log_org_id, no cascade) — the database refuses the cascade by
design. Retention beats hygiene; purging evidence is a deliberate
retention-workflow action, not a cleanup side effect.
"""

import contextlib
import logging
from typing import Any

from sqlalchemy import exists, text
from sqlalchemy.orm import Session

from common.models import Agent, User
from common.models.audit_log import AuditLog
from common.models.organization import Organization

logger = logging.getLogger("ai_identity.user_cleanup")

# Users that must never be deleted, regardless of matching patterns or inactivity.
PROTECTED_EMAILS = {
    "bisteroleg@gmail.com",
    "levaj2000@gmail.com",
}


def owners_with_audit_history(db: Session, users: list[User]) -> set:
    """Return the ids of users who own an org that still holds audit_log rows.

    These users must not be deleted: the owner_id cascade would try to drop
    the org, and audit_log.org_id (chain partition key) blocks it at the DB.
    """
    if not users:
        return set()
    rows = (
        db.query(Organization.owner_id)
        .filter(
            Organization.owner_id.in_([u.id for u in users]),
            exists().where(AuditLog.org_id == Organization.id),
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def delete_users_with_cascade(
    db: Session,
    users: list[User],
) -> dict[str, Any]:
    """Delete users and handle all FK relationships.

    Cascade-deleted automatically (via DB FKs):
        agents -> agent_keys, policies, upstream_credentials, agent_assignments
        org_memberships, compliance_reports

    Handled explicitly here (soft FK or missing ondelete):
        audit_log.agent_name  — denormalized before agent cascade
        audit_log.user_id     — nullified (soft FK, no constraint)
        qa_runs.user_id       — nullified (FK with no ondelete = RESTRICT)
        blocked_agents        — deleted (soft FK, orphan rows useless)
        dismissed_shadow_agents — deleted (soft FK, orphan rows useless)
        approval_requests     — deleted (soft FK, orphan rows useless)
    """
    if not users:
        return {"deleted_count": 0, "emails": [], "agents_removed": 0, "retained_for_evidence": []}

    # Filter out protected users as a safety net
    users = [u for u in users if u.email not in PROTECTED_EMAILS]

    # Evidence retention: skip users whose org still holds audit history
    # (owner_id cascade would hit fk_audit_log_org_id and abort the whole run).
    retained_ids = owners_with_audit_history(db, users)
    retained_emails = [u.email for u in users if u.id in retained_ids]
    users = [u for u in users if u.id not in retained_ids]
    if retained_emails:
        logger.info(
            "Evidence retention: skipping %d user(s) whose org holds audit history: %s",
            len(retained_emails),
            ", ".join(retained_emails),
        )
    if not users:
        return {
            "deleted_count": 0,
            "emails": [],
            "agents_removed": 0,
            "retained_for_evidence": retained_emails,
        }

    user_ids = [str(u.id) for u in users]
    emails = [u.email for u in users]

    # Count agents that will be cascade-deleted
    agents = db.query(Agent).filter(Agent.user_id.in_([u.id for u in users])).all()
    agent_count = len(agents)

    try:
        # 1. Disable immutability trigger for all audit_log updates
        db.execute(text("ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_update"))

        # 2. Denormalize agent_name into audit_log before cascade delete
        for agent in agents:
            db.query(AuditLog).filter(
                AuditLog.agent_id == agent.id,
                AuditLog.agent_name.is_(None),
            ).update({"agent_name": agent.name}, synchronize_session="fetch")

        # 3. Nullify audit_log.user_id (soft FK, preserved for history)
        for uid in user_ids:
            db.execute(
                text("UPDATE audit_log SET user_id = NULL WHERE user_id = :uid"), {"uid": uid}
            )

        # 4. Re-enable trigger
        db.execute(text("ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_update"))
    except Exception:
        with contextlib.suppress(Exception):
            db.execute(text("ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_update"))
        raise

    # 5. Nullify qa_runs.user_id (FK with no ondelete = RESTRICT)
    for uid in user_ids:
        db.execute(text("UPDATE qa_runs SET user_id = NULL WHERE user_id = :uid"), {"uid": uid})

    # 3. Delete soft-FK rows (no cascade, orphans are useless)
    for uid in user_ids:
        db.execute(text("DELETE FROM blocked_agents WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM dismissed_shadow_agents WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM approval_requests WHERE user_id = :uid"), {"uid": uid})

    # 4. Delete users — CASCADE handles agents->keys/policies/credentials/assignments,
    #    org_memberships, compliance_reports
    for uid in user_ids:
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})

    db.commit()
    db.expire_all()

    logger.info(
        "Deleted %d users (%d agents cascaded): %s",
        len(emails),
        agent_count,
        ", ".join(emails),
    )

    return {
        "deleted_count": len(emails),
        "emails": emails,
        "agents_removed": agent_count,
        "retained_for_evidence": retained_emails,
    }
