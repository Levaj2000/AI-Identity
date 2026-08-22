"""Edge registration + OCSF ingest — arrival-time verification tests.

The signer here replicates the cpex-ocsf-audit emitter's construction
(``sign::signing_input``): fingerprint = SHA-256 over the RFC 8785
canonical bytes of the event minus attestation ``fingerprint``/
``signatures`` and the two ``unmapped`` signature extras; signature =
ECDSA-P256-SHA256 (DER, base64) over the DSSE PAE of the same bytes.
Verification is exercised against records built independently of the
service's own helpers wherever the test is about catching tampering.
"""

import base64
import copy
import hashlib
import json
import uuid

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from api.app.services.edge_ingest import covered_bytes, dsse_pae
from common.models import EdgeAuditEvent, EdgeDeployment, OrgMembership

CHAIN_UID = "edge-test-chain-1"
STREAM_ID = "gw-t/boot-1"

# Fixed key scalar for deterministic tests (never a real credential)
SIGNING_KEY = ec.derive_private_key(0xC0FFEE, ec.SECP256R1())
OTHER_KEY = ec.derive_private_key(0xDECAF, ec.SECP256R1())


def key_pem(private_key) -> str:
    return (
        private_key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


def make_event(
    seq: int,
    uid: str,
    prev: tuple[str, str] | None,
    *,
    key=SIGNING_KEY,
    chain_uid: str = CHAIN_UID,
    key_id: str = "test-key-1",
) -> dict:
    """A minimal OCSF 6003 record, chained and signed like the emitter."""
    event = {
        "class_uid": 6003,
        "category_uid": 6,
        "type_uid": 600399,
        "action": "Allowed",
        "metadata": {"uid": uid, "version": "1.9.0"},
        "attestation_list": [
            {
                "uid": f"att-{uid}",
                "chain_uid": chain_uid,
                "authority_uid": "org-test",
            }
        ],
        "unmapped": {
            "cpex.stream": {
                "epoch": 1,
                "stream_id": STREAM_ID,
                "stream_seq": seq,
                "emission_seq": seq,
            }
        },
    }
    if prev is not None:
        prev_uid, prev_fp = prev
        event["attestation_list"][0]["prev_event"] = {
            "uid": prev_uid,
            "type_uid": 600399,
            "fingerprint": {"algorithm_id": 3, "value": prev_fp},
        }
    cb = covered_bytes(event)
    fingerprint = hashlib.sha256(cb).hexdigest()
    event["attestation_list"][0]["fingerprint"] = {
        "algorithm_id": 3,
        "encoding_id": 1,
        "serialization_id": 2,
        "value": fingerprint,
    }
    signature = key.sign(dsse_pae(cb), ec.ECDSA(hashes.SHA256()))
    event["unmapped"]["signature_b64"] = base64.b64encode(signature).decode()
    event["unmapped"]["signature_key_id"] = key_id
    return event


def make_chain(n: int, start: int = 1, **kwargs) -> list[dict]:
    events, prev = [], None
    for i in range(n):
        ev = make_event(start + i, f"rec-{start + i}", prev, **kwargs)
        events.append(ev)
        prev = (ev["metadata"]["uid"], ev["attestation_list"][0]["fingerprint"]["value"])
    return events


def ndjson(events: list[dict]) -> bytes:
    return b"\n".join(json.dumps(e).encode() for e in events)


@pytest.fixture
def org_admin(db_session, test_user):
    """test_user with an explicit owner membership in its org."""
    db_session.add(OrgMembership(org_id=test_user.org_id, user_id=test_user.id, role="owner"))
    db_session.commit()
    return test_user


@pytest.fixture
def edge(client, org_admin, auth_headers):
    """A registered edge; returns (edge_id, ingest_headers)."""
    resp = client.post(
        "/api/v1/edges",
        headers=auth_headers,
        json={
            "name": "Test Edge",
            "chain_uid": CHAIN_UID,
            "verify_key_pem": key_pem(SIGNING_KEY),
            "key_id": "test-key-1",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["ingest_key"].startswith("aid_edge_")
    return data["id"], {"Authorization": f"Bearer {data['ingest_key']}"}


# ── Registration ────────────────────────────────────────────────────


def test_register_requires_org_admin(client, db_session, test_user, auth_headers):
    from common.models import User

    member = User(id=uuid.uuid4(), email="member@example.com", role="member", tier="enterprise")
    member.org_id = test_user.org_id
    db_session.add(member)
    db_session.add(OrgMembership(org_id=test_user.org_id, user_id=member.id, role="member"))
    db_session.commit()

    resp = client.post(
        "/api/v1/edges",
        headers={"X-API-Key": "member@example.com"},
        json={"name": "E", "chain_uid": "c1", "verify_key_pem": key_pem(SIGNING_KEY)},
    )
    assert resp.status_code == 403


def test_register_rejects_non_p256_keys(client, org_admin, auth_headers):
    resp = client.post(
        "/api/v1/edges",
        headers=auth_headers,
        json={"name": "E", "chain_uid": "c-bad", "verify_key_pem": "not a pem"},
    )
    assert resp.status_code == 422

    rsa_pem = (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    resp = client.post(
        "/api/v1/edges",
        headers=auth_headers,
        json={"name": "E", "chain_uid": "c-rsa", "verify_key_pem": rsa_pem},
    )
    assert resp.status_code == 422
    assert "P-256" in resp.text


def test_register_rejects_duplicate_chain_uid(client, edge, auth_headers):
    resp = client.post(
        "/api/v1/edges",
        headers=auth_headers,
        json={"name": "E2", "chain_uid": CHAIN_UID, "verify_key_pem": key_pem(SIGNING_KEY)},
    )
    assert resp.status_code == 409


def test_list_and_revoke(client, edge, auth_headers):
    edge_id, ingest_headers = edge
    listed = client.get("/api/v1/edges", headers=auth_headers).json()["edges"]
    assert [e["id"] for e in listed] == [edge_id]
    assert "ingest_key" not in listed[0]  # show-once: never listed back

    resp = client.post(f"/api/v1/edges/{edge_id}/revoke", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

    resp = client.post("/api/v1/audit/ingest", headers=ingest_headers, content=b"{}")
    assert resp.status_code == 403


# ── Ingest auth ─────────────────────────────────────────────────────


def test_ingest_rejects_missing_and_unknown_keys(client, edge):
    assert client.post("/api/v1/audit/ingest", content=b"{}").status_code == 401
    resp = client.post(
        "/api/v1/audit/ingest",
        headers={"Authorization": "Bearer aid_edge_not-a-real-key"},
        content=b"{}",
    )
    assert resp.status_code == 401


# ── Verification outcomes ───────────────────────────────────────────


def test_happy_path_chain_verifies(client, db_session, edge):
    edge_id, headers = edge
    events = make_chain(3)
    resp = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events))
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["received"] == 3 and data["verified"] == 3 and data["quarantined"] == 0
    assert [r["status"] for r in data["results"]] == ["verified"] * 3
    assert [r["chain_position"] for r in data["results"]] == [1, 2, 3]

    rows = db_session.query(EdgeAuditEvent).order_by(EdgeAuditEvent.id).all()
    assert [r.verification_status for r in rows] == ["verified"] * 3
    assert rows[0].stream_seq == 1 and rows[2].stream_seq == 3
    assert rows[0].event["metadata"]["uid"] == "rec-1"

    dep = db_session.query(EdgeDeployment).one()
    assert dep.last_ingest_at is not None


def test_second_batch_resumes_chain_from_db(client, edge):
    _, headers = edge
    events = make_chain(4)
    client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events[:2]))
    resp = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events[2:]))
    data = resp.json()
    assert data["verified"] == 2
    assert [r["chain_position"] for r in data["results"]] == [3, 4]


def test_replay_is_reported_duplicate_not_restored(client, db_session, edge):
    _, headers = edge
    events = make_chain(2)
    client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events))
    resp = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events))
    data = resp.json()
    assert data["duplicates"] == 2 and data["verified"] == 0
    assert db_session.query(EdgeAuditEvent).count() == 2


def test_tampered_payload_is_quarantined(client, db_session, edge):
    _, headers = edge
    event = make_chain(1)[0]
    event["action"] = "Denied"  # tamper after signing
    resp = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson([event]))
    data = resp.json()
    assert data["quarantined"] == 1
    reason = data["results"][0]["reason"]
    assert "fingerprint mismatch" in reason
    row = db_session.query(EdgeAuditEvent).one()
    assert row.verification_status == "quarantined"
    assert row.chain_position is None
    assert row.event["action"] == "Denied"  # stored verbatim, flagged — never dropped


def test_wrong_key_signature_is_quarantined(client, edge):
    _, headers = edge
    event = make_event(1, "rec-1", None, key=OTHER_KEY)
    data = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson([event])).json()
    assert data["quarantined"] == 1
    assert "signature verification failed" in data["results"][0]["reason"]


def test_unsigned_record_is_quarantined(client, edge):
    _, headers = edge
    event = make_chain(1)[0]
    del event["attestation_list"]
    data = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson([event])).json()
    assert data["quarantined"] == 1
    assert "unsigned record" in data["results"][0]["reason"]


def test_stream_gap_is_recorded_as_anomaly_not_quarantined(client, db_session, edge):
    """A crypto-valid record after lost records verifies WITH the gap on it.

    Quarantining it would cascade: nothing after a crashed edge epoch
    could ever verify again. The gap is surfaced, never laundered.
    """
    _, headers = edge
    events = make_chain(2)
    head = (
        events[1]["metadata"]["uid"],
        events[1]["attestation_list"][0]["fingerprint"]["value"],
    )
    gapped = make_event(5, "rec-5", head)  # seq jumps 2 -> 5
    client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events))
    data = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson([gapped])).json()
    assert data["verified"] == 1 and data["quarantined"] == 0 and data["anomalies"] == 1
    result = data["results"][0]
    assert result["status"] == "verified" and result["chain_position"] == 3
    assert "stream_seq gap" in result["anomalies"]
    assert "expected 3, got 5" in result["anomalies"]
    row = db_session.query(EdgeAuditEvent).filter_by(metadata_uid="rec-5").one()
    assert row.verification_status == "verified" and "stream_seq gap" in row.anomalies


def test_chain_discontinuity_re_anchors_with_anomaly(client, edge):
    _, headers = edge
    events = make_chain(2)
    # Crypto-valid record whose prev_event doesn't match the head — the
    # crash-tail-loss shape: its predecessors were never delivered.
    orphan = make_event(3, "rec-3", ("lost-rec", "ab" * 32))
    successor = make_event(
        4,
        "rec-4",
        ("rec-3", orphan["attestation_list"][0]["fingerprint"]["value"]),
    )
    client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(events))
    data = client.post(
        "/api/v1/audit/ingest", headers=headers, content=ndjson([orphan, successor])
    ).json()
    assert [r["status"] for r in data["results"]] == ["verified", "verified"]
    assert "chain discontinuity" in data["results"][0]["anomalies"]
    # The chain re-anchored at the orphan: its successor verifies cleanly
    assert data["results"][1]["anomalies"] is None


def test_quarantined_record_does_not_become_chain_head(client, edge):
    _, headers = edge
    events = make_chain(2)
    tampered = copy.deepcopy(events[0])
    tampered["action"] = "Denied"
    # Tampered rec-1 first, then genuine rec-1 + rec-2: the genuine chain
    # must verify — the quarantined record must not have claimed the head
    # (its dedupe identity differs from nothing — same uid, so replace uid).
    tampered["metadata"]["uid"] = "rec-evil"
    data = client.post(
        "/api/v1/audit/ingest", headers=headers, content=ndjson([tampered] + events)
    ).json()
    assert [r["status"] for r in data["results"]] == ["quarantined", "verified", "verified"]


def test_chain_uid_mismatch_is_quarantined(client, edge):
    _, headers = edge
    event = make_event(1, "rec-1", None, chain_uid="some-other-chain")
    data = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson([event])).json()
    assert "chain_uid mismatch" in data["results"][0]["reason"]


def test_key_id_mismatch_is_quarantined(client, edge):
    _, headers = edge
    event = make_event(1, "rec-1", None, key_id="rogue-key")
    data = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson([event])).json()
    assert "signature_key_id mismatch" in data["results"][0]["reason"]


def test_unparseable_line_is_an_error_result(client, edge):
    _, headers = edge
    event = make_chain(1)[0]
    body = b"this is not json\n" + ndjson([event])
    data = client.post("/api/v1/audit/ingest", headers=headers, content=body).json()
    assert data["errors"] == 1 and data["verified"] == 1
    assert data["results"][0]["status"] == "error"


def test_batch_limits(client, edge, monkeypatch):
    from api.app.routers import edge_ingest as module

    _, headers = edge
    monkeypatch.setattr(module, "MAX_BATCH_RECORDS", 2)
    resp = client.post("/api/v1/audit/ingest", headers=headers, content=ndjson(make_chain(3)))
    assert resp.status_code == 413

    resp = client.post("/api/v1/audit/ingest", headers=headers, content=b"  \n  ")
    assert resp.status_code == 422


def test_other_orgs_admin_cannot_see_or_revoke_edge(client, edge, other_user, db_session):
    edge_id, _ = edge
    db_session.add(OrgMembership(org_id=other_user.org_id, user_id=other_user.id, role="owner"))
    db_session.commit()
    other_headers = {"X-API-Key": other_user.email}
    assert client.get("/api/v1/edges", headers=other_headers).json()["edges"] == []
    resp = client.post(f"/api/v1/edges/{edge_id}/revoke", headers=other_headers)
    assert resp.status_code == 404
