"""Tests for the forensic retention policy data model (v0.5.0).

Covers RetentionPolicy (immutable versions, one active per org), LegalHold,
and RetentionEvent (the retention_event record class). Rule-engine and
reaper behavior are API-layer concerns tested separately.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from common.models import (
    HOLD_STATUSES,
    POLICY_STATUSES,
    RETENTION_EVENT_TYPES,
    SAMPLING_ALG_V1,
    TOMBSTONE_REASONS,
    LegalHold,
    Organization,
    RetentionEvent,
    RetentionPolicy,
    User,
)


def _make_org(db_session, name="Test Org"):
    owner = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", role="owner")
    db_session.add(owner)
    db_session.flush()
    org = Organization(id=uuid.uuid4(), name=name, owner_id=owner.id)
    db_session.add(org)
    db_session.flush()
    return org


def _policy_kwargs(org_id, policy_id="retpol_test", version=1, status="draft"):
    return {
        "policy_id": policy_id,
        "org_id": org_id,
        "version": version,
        "status": status,
        "rules": [
            {
                "rule_id": "r_01",
                "selector": {"record_class": "audit", "decision": ["deny"]},
                "retain_for": "P13M",
                "redact_after": "P90D",
                "sampling": {"alg": SAMPLING_ALG_V1, "of": 100, "keep": 100},
                "hold_exempt": False,
            }
        ],
        "default_rule": {"retain_for": "P30D"},
        "created_by": "principal_test_001",
    }


def test_create_policy_defaults(db_session):
    org = _make_org(db_session)
    policy = RetentionPolicy(**_policy_kwargs(org.id))
    db_session.add(policy)
    db_session.commit()

    assert policy.id is not None
    assert policy.version == 1
    assert policy.status == "draft"
    assert policy.approvals == []
    assert policy.rules[0]["sampling"]["alg"] == "sha256-mod-v1"
    assert policy.created_at is not None
    assert policy.effective_at is not None


def test_one_active_policy_per_org(db_session):
    org = _make_org(db_session)
    db_session.add(RetentionPolicy(**_policy_kwargs(org.id, version=1, status="active")))
    db_session.commit()

    # A second active version for the same org violates the partial unique index.
    db_session.add(RetentionPolicy(**_policy_kwargs(org.id, version=2, status="active")))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # But active + superseded coexist fine (the normal version-rotation shape).
    db_session.add(RetentionPolicy(**_policy_kwargs(org.id, version=2, status="superseded")))
    db_session.commit()
    assert db_session.query(RetentionPolicy).count() == 2


def test_active_policies_are_per_org(db_session):
    org_a = _make_org(db_session, name="Org A")
    org_b = _make_org(db_session, name="Org B")
    db_session.add(RetentionPolicy(**_policy_kwargs(org_a.id, status="active")))
    db_session.add(RetentionPolicy(**_policy_kwargs(org_b.id, status="active")))
    db_session.commit()
    assert db_session.query(RetentionPolicy).count() == 2


def test_policy_version_uniqueness(db_session):
    org = _make_org(db_session)
    db_session.add(RetentionPolicy(**_policy_kwargs(org.id, version=1, status="draft")))
    db_session.commit()
    db_session.add(RetentionPolicy(**_policy_kwargs(org.id, version=1, status="superseded")))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_legal_hold(db_session):
    org = _make_org(db_session)
    hold = LegalHold(
        org_id=org.id,
        selector={
            "record_ids": [101, 102],
            "agent_id": str(uuid.uuid4()),
            "time_window": {"from": "2026-01-01T00:00:00Z", "to": "2026-06-01T00:00:00Z"},
        },
        placed_by="principal_test_001",
    )
    db_session.add(hold)
    db_session.commit()

    assert hold.status == "active"
    assert hold.released_at is None
    assert hold.released_by is None
    assert hold.selector["record_ids"] == [101, 102]


def test_release_legal_hold(db_session):
    org = _make_org(db_session)
    hold = LegalHold(org_id=org.id, selector={}, placed_by="principal_test_001")
    db_session.add(hold)
    db_session.commit()

    hold.status = "released"
    hold.released_by = "principal_test_002"  # must differ from placed_by (API-enforced)
    hold.release_reason = "litigation settled"
    db_session.commit()

    assert hold.released_by != hold.placed_by


def test_create_tombstone_event(db_session):
    org = _make_org(db_session)
    event = RetentionEvent(
        org_id=org.id,
        event_type="tombstone",
        payload={
            "entry_hash": "ab" * 32,
            "entry_hash_org": "cd" * 32,
            "audit_id": 4242,
            "org_chain_seq": 4242,
            "merkle_root": "ef" * 32,
            "reason": "retention_elapsed",
            "rule_id": "r_01",
            "checkpoint_id": str(uuid.uuid4()),
        },
        created_by="reaper",
    )
    db_session.add(event)
    db_session.commit()

    fetched = db_session.query(RetentionEvent).one()
    assert fetched.event_type == "tombstone"
    assert fetched.payload["reason"] in TOMBSTONE_REASONS
    assert fetched.payload["audit_id"] == 4242


def test_create_redaction_receipt_event(db_session):
    org = _make_org(db_session)
    event = RetentionEvent(
        org_id=org.id,
        event_type="redaction_receipt",
        payload={"scope": "stored", "redacted_fields": ["request_metadata.ip"]},
        created_by="reaper",
    )
    db_session.add(event)
    db_session.commit()

    assert event.payload["scope"] == "stored"


def test_org_cascade_deletes_retention_rows(db_session):
    org = _make_org(db_session)
    db_session.add(RetentionPolicy(**_policy_kwargs(org.id, status="active")))
    db_session.add(LegalHold(org_id=org.id, selector={}, placed_by="principal_test_001"))
    db_session.add(
        RetentionEvent(
            org_id=org.id,
            event_type="policy_published",
            payload={},
            created_by="principal_test_001",
        )
    )
    db_session.commit()

    db_session.delete(org)
    db_session.commit()

    assert db_session.query(RetentionPolicy).count() == 0
    assert db_session.query(LegalHold).count() == 0
    assert db_session.query(RetentionEvent).count() == 0


def test_design_constants():
    assert {
        "retention_elapsed",
        "sampling",
        "erasure_request",
        "tenant_offboarding",
        "plan_ceiling",
    } == TOMBSTONE_REASONS
    assert {"draft", "active", "superseded"} == POLICY_STATUSES
    assert {"active", "released"} == HOLD_STATUSES
    assert {
        "tombstone",
        "redaction_receipt",
        "hold_placed",
        "hold_released",
        "policy_published",
    } == RETENTION_EVENT_TYPES
    assert SAMPLING_ALG_V1 == "sha256-mod-v1"
