"""Integration tests for POST /api/v1/attestations.

End-to-end: seed a per-org audit chain, hit the endpoint with the
org-owner's credentials, verify the returned DSSE envelope with the
local public key, and sanity-check the persisted row.

Uses the local-PEM signing backend — KMS is covered separately in
``common/tests/test_forensic_attestation.py``.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from api.app.routers import attestations as attestations_module
from common.audit import create_audit_entry
from common.models import Agent, ForensicAttestation, Organization, OrgMembership, User
from common.schemas.forensic_attestation import DSSEEnvelope, verify_envelope

# ── Fixtures ────────────────────────────────────────────────────────


OWNER_EMAIL = "owner@example.test"
OTHER_OWNER_EMAIL = "owner-other@example.test"


@pytest.fixture
def ec_keypair():
    """Fresh P-256 keypair for the test signer."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pem_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem_private, pem_public


@pytest.fixture(autouse=True)
def _signer_cache_reset():
    """Ensure each test resolves a fresh signer against current settings."""
    attestations_module._reset_signer_cache_for_tests()
    yield
    attestations_module._reset_signer_cache_for_tests()


@pytest.fixture
def local_signer(monkeypatch, ec_keypair):
    """Point the router at the in-process PEM signer."""
    pem_private, pem_public = ec_keypair
    from common.config.settings import settings

    monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
    monkeypatch.setattr(settings, "forensic_signing_key_pem", pem_private, raising=False)
    return pem_public


@pytest.fixture
def seeded_org(db_session):
    """One org with an owner, an agent, and a few audit rows."""
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    owner = User(id=uuid.uuid4(), email=OWNER_EMAIL, role="owner", tier="enterprise")
    db_session.add(owner)
    db_session.flush()

    org = Organization(id=org_id, name="Test Org", owner_id=owner.id, tier="business")
    db_session.add(org)
    db_session.flush()

    owner.org_id = org_id
    db_session.add(OrgMembership(org_id=org_id, user_id=owner.id, role="owner"))

    agent = Agent(
        id=uuid.uuid4(),
        user_id=owner.id,
        org_id=org_id,
        name="A",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add(agent)
    db_session.commit()

    entries = []
    for _ in range(3):
        entries.append(
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint="/v1/chat",
                method="POST",
                decision="allow",
                request_metadata={"model": "gpt-4"},
            )
        )
    return {"org_id": org_id, "owner": owner, "agent": agent, "entries": entries}


# ── Happy path ──────────────────────────────────────────────────────


class TestSignHappyPath:
    def test_sign_returns_verifiable_envelope(self, client, db_session, seeded_org, local_signer):
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)

        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 201, resp.text
        payload = resp.json()

        # Response shape
        assert payload["event_count"] == 3
        assert payload["first_audit_id"] == entries[0].id
        assert payload["last_audit_id"] == entries[-1].id
        assert payload["signer_key_id"].startswith("local:")

        # Verify the envelope cryptographically with the public key
        envelope = DSSEEnvelope.model_validate(payload["envelope"])
        parsed = verify_envelope(envelope, local_signer)
        assert parsed.evidence_chain_hash == entries[-1].entry_hash
        assert parsed.event_count == 3
        assert parsed.session_id == uuid.UUID(body["session_id"])

    def test_persists_resolved_audit_log_ids(self, client, db_session, seeded_org, local_signer):
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)

        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 201

        row = db_session.query(ForensicAttestation).one()
        # Purge-resilience guarantee: the concrete row IDs are frozen
        # at sign time, not just the range bounds.
        assert row.audit_log_ids == [e.id for e in entries]
        assert row.event_count == 3

    def test_envelope_payload_roundtrips_to_json(self, client, seeded_org, local_signer):
        """DSSE payload must base64-decode to the canonical JSON we signed."""
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)

        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 201

        envelope = resp.json()["envelope"]
        decoded = base64.b64decode(envelope["payload"])
        # JCS sorts keys alphabetically — "evidence_chain_hash" comes
        # before "first_audit_id" before "schema_version".
        assert b'"evidence_chain_hash"' in decoded
        assert b'"schema_version":1' in decoded


# ── Idempotency ─────────────────────────────────────────────────────


class TestIdempotency:
    def test_resign_same_session_returns_existing(
        self, client, db_session, seeded_org, local_signer
    ):
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)

        first = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert first.status_code == 201
        first_id = first.json()["id"]

        # Re-POST the same session — server must return the same row,
        # not sign again.
        second = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert second.status_code == 201
        assert second.json()["id"] == first_id
        assert db_session.query(ForensicAttestation).count() == 1


# ── Validation + AuthZ ──────────────────────────────────────────────


class TestValidation:
    def test_empty_range_rejected(self, client, db_session, seeded_org, local_signer):
        entries = seeded_org["entries"]
        # A range above all existing rows → no rows → 400.
        body = _sign_body(
            seeded_org,
            entries[-1].id + 1000,
            entries[-1].id + 1001,
        )
        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 400
        assert "no audit_log rows" in resp.json()["error"]["message"]

    def test_inverted_range_rejected(self, client, seeded_org, local_signer):
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[-1].id, entries[0].id)
        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 400

    def test_cross_org_range_rejected(self, client, db_session, seeded_org, local_signer):
        """Range containing another org's audit rows must be rejected."""
        other_owner = User(
            id=uuid.uuid4(),
            email=OTHER_OWNER_EMAIL,
            role="owner",
            tier="enterprise",
        )
        db_session.add(other_owner)
        db_session.flush()
        other_org_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        other_org = Organization(
            id=other_org_id, name="Other", owner_id=other_owner.id, tier="business"
        )
        db_session.add(other_org)
        db_session.flush()
        other_agent = Agent(
            id=uuid.uuid4(),
            user_id=other_owner.id,
            org_id=other_org_id,
            name="B",
            status="active",
            capabilities=[],
            metadata_={},
        )
        db_session.add(other_agent)
        db_session.commit()
        cross_entry = create_audit_entry(
            db_session,
            agent_id=other_agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        entries = seeded_org["entries"]
        # Ask to attest over a range that now includes the other org's row.
        body = _sign_body(seeded_org, entries[0].id, cross_entry.id)
        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 400
        assert "another org" in resp.json()["error"]["message"]

    def test_non_admin_rejected(self, client, db_session, seeded_org, local_signer):
        """Plain org members cannot sign attestations — owner/admin only."""
        member = User(
            id=uuid.uuid4(),
            email="member@example.test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(member)
        db_session.flush()
        db_session.add(OrgMembership(org_id=seeded_org["org_id"], user_id=member.id, role="member"))
        db_session.commit()

        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": "member@example.test"},
        )
        assert resp.status_code == 403


# ── Signer unavailable ──────────────────────────────────────────────


class TestSignerUnavailable:
    def test_no_signer_returns_503(self, client, seeded_org, monkeypatch):
        """Neither KMS nor local key configured → 503, not 500."""
        from common.config.settings import settings

        monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
        monkeypatch.setattr(settings, "forensic_signing_key_pem", "", raising=False)

        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        resp = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 503


# ── Retrieval (#264) ────────────────────────────────────────────────


class TestGetAttestationBySession:
    def test_owner_fetches_own_attestation(self, client, seeded_org, local_signer):
        """Happy path: org owner POSTs, then GETs back the envelope."""
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        post = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert post.status_code == 201

        get = client.get(
            f"/api/v1/sessions/{body['session_id']}/attestation",
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert get.status_code == 200, get.text
        assert get.json()["id"] == post.json()["id"]
        assert get.json()["envelope"] == post.json()["envelope"]

    def test_plain_member_can_read(self, client, db_session, seeded_org, local_signer):
        """Read access is any-role — members can view their org's evidence."""
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        post = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert post.status_code == 201

        reader = User(
            id=uuid.uuid4(),
            email="reader@example.test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(reader)
        db_session.flush()
        db_session.add(OrgMembership(org_id=seeded_org["org_id"], user_id=reader.id, role="member"))
        db_session.commit()

        get = client.get(
            f"/api/v1/sessions/{body['session_id']}/attestation",
            headers={"X-API-Key": "reader@example.test"},
        )
        assert get.status_code == 200
        assert get.json()["id"] == post.json()["id"]

    def test_unknown_session_returns_404(self, client, seeded_org):
        resp = client.get(
            f"/api/v1/sessions/{uuid.uuid4()}/attestation",
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 404

    def test_other_org_session_returns_404_not_403(
        self, client, db_session, seeded_org, local_signer
    ):
        """Tenancy boundary: 'exists but not yours' must look like
        'does not exist' to avoid leaking cross-org session ids.
        """
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        post = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert post.status_code == 201

        # Outsider: authenticated user with no membership in seeded_org.
        outsider_org_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        outsider = User(
            id=uuid.uuid4(),
            email="outsider@example.test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(outsider)
        db_session.flush()
        outsider_org = Organization(
            id=outsider_org_id,
            name="Outsider Org",
            owner_id=outsider.id,
            tier="business",
        )
        db_session.add(outsider_org)
        db_session.add(OrgMembership(org_id=outsider_org_id, user_id=outsider.id, role="owner"))
        db_session.commit()

        resp = client.get(
            f"/api/v1/sessions/{body['session_id']}/attestation",
            headers={"X-API-Key": "outsider@example.test"},
        )
        assert resp.status_code == 404

    def test_user_with_no_memberships_returns_404(
        self, client, db_session, seeded_org, local_signer
    ):
        """Authenticated but memberless users must not bypass the filter
        (empty-IN on some DBs matches everything). Short-circuit with 404.
        """
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        post = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert post.status_code == 201

        loner = User(
            id=uuid.uuid4(),
            email="loner@example.test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(loner)
        db_session.commit()

        resp = client.get(
            f"/api/v1/sessions/{body['session_id']}/attestation",
            headers={"X-API-Key": "loner@example.test"},
        )
        assert resp.status_code == 404

    def test_platform_admin_sees_any_org(self, client, db_session, seeded_org, local_signer):
        """role=='admin' bypasses the org filter — ops can inspect any tenant."""
        entries = seeded_org["entries"]
        body = _sign_body(seeded_org, entries[0].id, entries[-1].id)
        post = client.post(
            "/api/v1/attestations",
            json=body,
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert post.status_code == 201

        platform_admin = User(
            id=uuid.uuid4(),
            email="admin@example.test",
            role="admin",
            tier="enterprise",
        )
        db_session.add(platform_admin)
        db_session.commit()

        resp = client.get(
            f"/api/v1/sessions/{body['session_id']}/attestation",
            headers={"X-API-Key": "admin@example.test"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == post.json()["id"]


# ── Helper ──────────────────────────────────────────────────────────


def _sign_body(seeded_org, first_id: int, last_id: int) -> dict:
    now = datetime.now(UTC)
    return {
        "session_id": str(uuid.uuid4()),
        "org_id": str(seeded_org["org_id"]),
        "first_audit_id": first_id,
        "last_audit_id": last_id,
        "session_start": (now - timedelta(minutes=5)).isoformat(),
        "session_end": now.isoformat(),
    }
