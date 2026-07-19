"""Evidence retention in user cleanup (Sentry PYTHON-FASTAPI-Y).

A user whose org still holds audit_log rows must never be deleted:
organizations.owner_id cascades on user delete, and audit_log.org_id
(the tamper-evident chain's partition key, fk_audit_log_org_id in
Postgres) blocks the cascade — so before this filter existed, the
nightly cleanup cron aborted with a ForeignKeyViolation every run.

Design decision (2026-07-18): retention beats hygiene. The cleanup
skips these users; purging evidence is a deliberate retention-workflow
action, never a cron side effect.
"""

import hashlib
import uuid

from common.models.audit_log import AuditLog
from common.models.organization import Organization
from common.models.user import User
from common.queries.user_cleanup import delete_users_with_cascade, owners_with_audit_history


def _user(db_session, email):
    user = User(id=uuid.uuid4(), email=email, role="member", tier="free")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _org(db_session, owner, name):
    org = Organization(name=name, owner_id=owner.id)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


def _audit_row(db_session, org):
    db_session.add(
        AuditLog(
            agent_id=uuid.uuid4(),
            org_id=org.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
            entry_hash=hashlib.sha256(f"evt-{org.id}".encode()).hexdigest(),
            prev_hash="GENESIS",
        )
    )
    db_session.commit()


def test_owners_with_audit_history_detects_only_orgs_with_rows(db_session):
    with_history = _user(db_session, "with-history@example.com")
    without_history = _user(db_session, "without-history@example.com")
    org_a = _org(db_session, with_history, "Org With Evidence")
    _org(db_session, without_history, "Org Without Evidence")
    _audit_row(db_session, org_a)

    retained = owners_with_audit_history(db_session, [with_history, without_history])

    assert retained == {with_history.id}


def test_cleanup_retains_user_whose_org_holds_audit_history(db_session):
    owner = _user(db_session, "inactive-owner@example.com")
    org = _org(db_session, owner, "Evidence Org")
    _audit_row(db_session, org)

    result = delete_users_with_cascade(db_session, [owner])

    assert result["deleted_count"] == 0
    assert result["emails"] == []
    assert result["retained_for_evidence"] == ["inactive-owner@example.com"]
    # User, org, and the audit row all survive
    assert db_session.query(User).filter(User.id == owner.id).count() == 1
    assert db_session.query(Organization).filter(Organization.id == org.id).count() == 1
    assert db_session.query(AuditLog).filter(AuditLog.org_id == org.id).count() == 1


def test_empty_input_reports_empty_retention(db_session):
    result = delete_users_with_cascade(db_session, [])
    assert result["retained_for_evidence"] == []
    assert result["deleted_count"] == 0
