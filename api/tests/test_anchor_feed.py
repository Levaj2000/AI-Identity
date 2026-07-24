"""Public Evidence Anchor checkpoint feed (anchor_feed.py).

The feed is the "someone else already holds the checkpoint" guarantee: it must
be reachable with no auth, serve exactly the envelope a Case File bundle
ships, page stably in append-only (ascending) order, and answer the
split-view spot check by merkle_root.
"""

from __future__ import annotations

import datetime
import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.config.settings import settings
from common.forensic.anchor_service import assemble_evidence, create_checkpoint
from common.models.audit_log import AuditLog
from common.models.organization import Organization

FEED = "/evidence-anchor/checkpoints"


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


def _org_with_rows(db, test_user, n, name="Feed Org"):
    org = Organization(name=name, owner_id=test_user.id)
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
                entry_hash=hashlib.sha256(f"f-{org.id}-{i}".encode()).hexdigest(),
                prev_hash="GENESIS" if i == 0 else "x" * 64,
            )
        )
    db.commit()
    return org


def _checkpoint(db, org, *, signed_at=None, max_batch=1000):
    cp = create_checkpoint(db, org.id, max_batch=max_batch, now=signed_at)
    assert cp is not None
    return cp


def test_feed_requires_no_auth_and_serves_bundle_identical_envelope(
    client, db_session, test_user, local_signer
):
    org = _org_with_rows(db_session, test_user, 5)
    cp = _checkpoint(db_session, org)

    resp = client.get(FEED)  # no auth header of any kind
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=60"
    body = resp.json()
    assert body["total"] == 1
    entry = body["checkpoints"][0]

    # The feed entry is the same artifact the Case File bundle ships — the
    # cross-check between a bundle and the public history must be exact.
    bundle = assemble_evidence(db_session, org.id, [cp.audit_log_ids[0]])
    assert entry["merkle_root"] == bundle["checkpoints"][0]["merkle_root"]
    assert entry["envelope"] == bundle["checkpoints"][0]["envelope"]

    # Indexing mirrors only — never the raw batch internals.
    assert entry["org_id"] == str(org.id)
    assert entry["tree_size"] == 5
    assert "leaves" not in entry
    assert "audit_log_ids" not in entry


def test_feed_orders_ascending_and_pages_stably(client, db_session, test_user, local_signer):
    org = _org_with_rows(db_session, test_user, 9)
    t0 = datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC)
    for i in range(3):
        _checkpoint(db_session, org, max_batch=3, signed_at=t0 + datetime.timedelta(minutes=15 * i))

    first = client.get(FEED, params={"limit": 2, "offset": 0}).json()
    rest = client.get(FEED, params={"limit": 2, "offset": 2}).json()
    signed = [c["signed_at"] for c in first["checkpoints"] + rest["checkpoints"]]
    assert first["total"] == rest["total"] == 3
    assert len(signed) == 3
    assert signed == sorted(signed)  # oldest first — append-only pages never shift
    roots = [c["merkle_root"] for c in first["checkpoints"] + rest["checkpoints"]]
    assert len(set(roots)) == 3


def test_feed_filters_by_org_and_time_range(client, db_session, test_user, local_signer):
    org_a = _org_with_rows(db_session, test_user, 2, name="Org A")
    org_b = _org_with_rows(db_session, test_user, 2, name="Org B")
    t0 = datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC)
    t1 = datetime.datetime(2026, 7, 2, tzinfo=datetime.UTC)
    _checkpoint(db_session, org_a, signed_at=t0)
    cp_b = _checkpoint(db_session, org_b, signed_at=t1)

    by_org = client.get(FEED, params={"org_id": str(org_b.id)}).json()
    assert by_org["total"] == 1
    assert by_org["checkpoints"][0]["merkle_root"] == cp_b.merkle_root

    windowed = client.get(FEED, params={"since": t0.isoformat(), "until": t1.isoformat()}).json()
    assert windowed["total"] == 1
    assert windowed["checkpoints"][0]["org_id"] == str(org_a.id)


def test_split_view_spot_check_by_root(client, db_session, test_user, local_signer):
    org = _org_with_rows(db_session, test_user, 4)
    cp = _checkpoint(db_session, org)

    hit = client.get(f"{FEED}/{cp.merkle_root}")
    assert hit.status_code == 200
    assert hit.json()["envelope"] == cp.envelope

    miss = client.get(f"{FEED}/{'0' * 64}")
    assert miss.status_code == 404
    assert "split-view" in miss.json()["error"]["message"]

    # Junk that isn't a sha256 hex root is rejected by validation, not queried.
    assert client.get(f"{FEED}/not-a-root").status_code == 422
