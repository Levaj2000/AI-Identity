"""Shared user deletion utility — handles all FK relationships safely.

Used by both the one-time purge script and the automated cleanup cron.
Preserves audit_log rows (soft FK) and denormalizes agent_name before deletion.
"""

import contextlib
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from common.models import Agent, User
from common.models.audit_log import AuditLog

logger = logging.getLogger("ai_identity.user_cleanup")

# Users that must never be deleted, regardless of matching patterns or inactivity.
PROTECTED_EMAILS = {
    "bisteroleg@gmail.com",
    "levaj2000@gmail.com",
}


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
        return {"deleted_count": 0, "emails": [], "agents_removed": 0}

    # Filter out protected users as a safety net
    users = [u for u in users if u.email not in PROTECTED_EMAILS]
    if not users:
        return {"deleted_count": 0, "emails": [], "agents_removed": 0}

    user_ids = [str(u.id) for u in users]
    emails = [u.email for u in users]

    # Count agents that will be cascade-deleted
    agents = db.query(Agent).filter(Agent.user_id.in_([u.id for u in users])).all()
    agent_count = len(agents)

    try:
        # 1. Denormalize agent_name into audit_log before cascade delete
        db.execute(text("ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_update"))

        for agent in agents:
            db.query(AuditLog).filter(
                AuditLog.agent_id == agent.id,
                AuditLog.agent_name.is_(None),
            ).update({"agent_name": agent.name}, synchronize_session="fetch")

        db.execute(text("ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_update"))
    except Exception:
        # Re-enable trigger even on error
        with contextlib.suppress(Exception):
            db.execute(text("ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_update"))
        raise

    # 2. Nullify soft-FK references that would block deletion
    for uid in user_ids:
        db.execute(text("UPDATE qa_runs SET user_id = NULL WHERE user_id = :uid"), {"uid": uid})
        db.execute(text("UPDATE audit_log SET user_id = NULL WHERE user_id = :uid"), {"uid": uid})

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
    }
