"""Evidence Anchor checkpoint cron endpoint (#408)."""

from __future__ import annotations

import functools
import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from api.app.routers import anchor_cron
from common.config.settings import settings
from common.forensic import anchor_service
from common.models.audit_checkpoint import AuditCheckpoint
from common.models.audit_log import AuditLog
from common.models.organization import Organization

ENDPOINT = "/api/internal/evidence-anchor/checkpoint"


@pytest.fixture
def local_signer(monkeypatch):
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
    monkeypatch.setattr(settings, "forensic_signing_key_pem", pem, raising=False)


def _org_with_rows(db, test_user, n):
    org = Organization(name="Anchor Org", owner_id=test_user.id)
    db.add(org)
    db.commit()
    db.refresh(org)
    for i in range(n):
        db.add(
            AuditLog(
                agent_id=test_user.id,
                org_id=org.id,
                endpoint="/v1/chat",
                method="POST",
                decision="allow",
                request_metadata={},
                entry_hash=hashlib.sha256(f"c-{org.id}-{i}".encode()).hexdigest(),
                prev_hash="GENESIS" if i == 0 else "x" * 64,
            )
        )
    db.commit()
    return org


def test_requires_internal_key(client):
    assert client.post(ENDPOINT).status_code == 401


def test_rejects_bad_key(client, mock_internal_service_key):
    resp = client.post(ENDPOINT, headers={"x-internal-key": "wrong"})
    assert resp.status_code == 401


def test_emits_checkpoint(client, db_session, test_user, mock_internal_service_key, local_signer):
    org = _org_with_rows(db_session, test_user, 12)

    resp = client.post(ENDPOINT, headers={"x-internal-key": "test-internal-key-xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["checkpoints_created"] == 1
    assert body["events_anchored"] == 12

    cp = db_session.query(AuditCheckpoint).filter(AuditCheckpoint.org_id == org.id).one()
    assert cp.tree_size == 12

    # Second run with nothing new → no new checkpoints.
    again = client.post(ENDPOINT, headers={"x-internal-key": "test-internal-key-xyz"})
    assert again.json()["checkpoints_created"] == 0


def test_backlog_drain_queries_high_water_mark_once_per_org(
    client, db_session, test_user, mock_internal_service_key, local_signer, monkeypatch
):
    """A multi-batch drain must not re-run the max(last_audit_id) lookup per batch.

    Regression for the N+1 Sentry flagged on this endpoint: the high-water mark
    is resolved once per org and then threaded forward across the drain.
    """
    org = _org_with_rows(db_session, test_user, 12)

    # Force several batches out of a small org by shrinking the batch size.
    monkeypatch.setattr(
        anchor_cron,
        "create_checkpoint",
        functools.partial(anchor_service.create_checkpoint, max_batch=5),
    )

    # Spy on the high-water-mark lookup that create_checkpoint calls internally.
    lookups: list = []
    real_last_anchored = anchor_service._last_anchored_id

    def _counting_last_anchored(db, org_id):
        lookups.append(org_id)
        return real_last_anchored(db, org_id)

    monkeypatch.setattr(anchor_service, "_last_anchored_id", _counting_last_anchored)

    resp = client.post(ENDPOINT, headers={"x-internal-key": "test-internal-key-xyz"})
    assert resp.status_code == 200
    body = resp.json()

    # 12 rows / batch of 5 → three contiguous checkpoints, all 12 events anchored.
    assert body["checkpoints_created"] == 3
    assert body["events_anchored"] == 12
    # The N+1 fix: one lookup for the org, not one per batch.
    assert lookups == [org.id]
