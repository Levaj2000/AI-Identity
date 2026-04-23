"""Tests for the compliance export API.

Foundation PR — endpoints are live against `compliance_exports`, the
builder runs inline via BackgroundTasks (TestClient drains them
synchronously on response), and the archive is signed + downloadable.
Profile-specific artifacts are still placeholders; those tests land
with the per-profile builder PRs.
"""

from __future__ import annotations

import base64
import io
import json
import uuid
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.compliance.manifest import EXPORT_MANIFEST_PAYLOAD_TYPE
from common.models import Agent, ComplianceExport, Organization, OrgMembership, User
from common.schemas.forensic_attestation import pae

ORG_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ORG_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER_A_EMAIL = "owner-a@example.test"
OWNER_B_EMAIL = "owner-b@example.test"
MEMBER_A_EMAIL = "member-a@example.test"
ADMIN_EMAIL = "admin@example.test"


# ── Signer fixture (local PEM) ───────────────────────────────────────


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


@pytest.fixture
def local_signer(monkeypatch, ec_keypair):
    """Point the builder at the in-process PEM signer."""
    pem_private, pem_public = ec_keypair
    from common.config.settings import settings

    monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
    monkeypatch.setattr(settings, "forensic_signing_key_pem", pem_private, raising=False)
    return pem_public


@pytest.fixture
def archive_dir(tmp_path, monkeypatch):
    """Redirect archive writes to a test tmp dir."""
    from common.config.settings import settings

    target = tmp_path / "compliance-exports"
    monkeypatch.setattr(settings, "compliance_export_archive_dir", str(target), raising=False)
    return target


@pytest.fixture(autouse=True)
def _background_session_uses_test_engine(monkeypatch):
    """Point the router's background-task session factory at the test
    sessionmaker so BackgroundTasks writes land in the same in-memory
    SQLite that the request session reads from.
    """
    from api.app.routers import compliance_exports as compliance_exports_module
    from api.tests.conftest import TestSessionLocal

    monkeypatch.setattr(
        compliance_exports_module,
        "_background_session_factory",
        TestSessionLocal,
        raising=True,
    )


# ── Seed: two orgs with agents ───────────────────────────────────────


@pytest.fixture
def two_orgs(db_session):
    owner_a = User(id=uuid.uuid4(), email=OWNER_A_EMAIL, role="owner", tier="enterprise")
    owner_b = User(id=uuid.uuid4(), email=OWNER_B_EMAIL, role="owner", tier="enterprise")
    member_a = User(id=uuid.uuid4(), email=MEMBER_A_EMAIL, role="owner", tier="enterprise")
    admin = User(id=uuid.uuid4(), email=ADMIN_EMAIL, role="admin", tier="enterprise")
    db_session.add_all([owner_a, owner_b, member_a, admin])
    db_session.flush()

    org_a = Organization(id=ORG_A_ID, name="Org A", owner_id=owner_a.id, tier="business")
    org_b = Organization(id=ORG_B_ID, name="Org B", owner_id=owner_b.id, tier="business")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    owner_a.org_id = ORG_A_ID
    owner_b.org_id = ORG_B_ID
    member_a.org_id = ORG_A_ID
    admin.org_id = ORG_A_ID  # primary org — platform admin still needs one for v1
    db_session.add_all(
        [
            OrgMembership(org_id=ORG_A_ID, user_id=owner_a.id, role="owner"),
            OrgMembership(org_id=ORG_B_ID, user_id=owner_b.id, role="owner"),
            OrgMembership(org_id=ORG_A_ID, user_id=member_a.id, role="member"),
            OrgMembership(org_id=ORG_A_ID, user_id=admin.id, role="member"),
        ]
    )

    agent_a = Agent(
        id=uuid.uuid4(),
        user_id=owner_a.id,
        org_id=ORG_A_ID,
        name="A",
        status="active",
        capabilities=[],
        metadata_={},
    )
    agent_b = Agent(
        id=uuid.uuid4(),
        user_id=owner_b.id,
        org_id=ORG_B_ID,
        name="B",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add_all([agent_a, agent_b])
    db_session.commit()
    return {
        "owner_a": owner_a,
        "owner_b": owner_b,
        "member_a": member_a,
        "admin": admin,
        "agent_a": agent_a,
        "agent_b": agent_b,
    }


def _valid_body(**overrides) -> dict:
    now = datetime.now(UTC)
    body = {
        "profile": "soc2_tsc_2017",
        "audit_period_start": (now - timedelta(days=30)).isoformat(),
        "audit_period_end": now.isoformat(),
        "agent_ids": None,
    }
    body.update(overrides)
    return body


# ── Happy path: POST → builds → GET ready ────────────────────────────


class TestCreateAndBuild:
    def test_post_returns_202_with_job(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["status"] in ("queued", "ready")  # build ran inline
        assert body["org_id"] == str(ORG_A_ID)
        assert body["profile"] == "soc2_tsc_2017"

    def test_build_reaches_ready_and_signs_manifest(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]

        # BackgroundTasks drain by the time TestClient returns; poll once.
        got = client.get(
            f"/api/v1/exports/{export_id}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert got.status_code == 200, got.text
        body = got.json()
        assert body["status"] == "ready"
        assert body["archive_sha256"] is not None
        assert body["archive_bytes"] > 0
        env = body["manifest_envelope"]
        assert env["payloadType"] == EXPORT_MANIFEST_PAYLOAD_TYPE
        assert len(env["signatures"]) == 1

    def test_manifest_signature_verifies_against_public_key(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        got = client.get(
            f"/api/v1/exports/{export_id}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        env = got["manifest_envelope"]

        payload_bytes = base64.b64decode(env["payload"])
        signing_input = pae(env["payloadType"], payload_bytes)
        signature = base64.b64decode(env["signatures"][0]["sig"])

        public_key = serialization.load_pem_public_key(local_signer)
        # Raises on failure — the assertion *is* the verify call.
        public_key.verify(
            signature,
            signing_input,
            ec.ECDSA(
                __import__("cryptography.hazmat.primitives.hashes", fromlist=["SHA256"]).SHA256()
            ),
        )

    def test_manifest_commits_to_artifact_hashes(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        got = client.get(
            f"/api/v1/exports/{export_id}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        env = got["manifest_envelope"]
        manifest = json.loads(base64.b64decode(env["payload"]))
        # Placeholder builder writes README.md and PLACEHOLDER.txt; the
        # manifest must include both, with non-empty hashes.
        paths = {a["path"] for a in manifest["artifacts"]}
        assert "README.md" in paths
        assert "PLACEHOLDER.txt" in paths
        for artifact in manifest["artifacts"]:
            assert len(artifact["sha256"]) == 64
            assert artifact["bytes"] > 0


# ── Download endpoint ────────────────────────────────────────────────


class TestDownload:
    def test_download_after_ready_returns_zip(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]

        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        names = set(zf.namelist())
        assert {"README.md", "PLACEHOLDER.txt", "manifest.json", "manifest.dsse.json"} <= names

    def test_download_roundtrip_matches_archive_sha256(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        meta = client.get(
            f"/api/v1/exports/{export_id}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        import hashlib

        assert hashlib.sha256(dl.content).hexdigest() == meta["archive_sha256"]

    def test_download_wrong_org_returns_404(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        other = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_B_EMAIL},
        )
        assert other.status_code == 404


# ── Idempotency (409 on in-flight duplicate) ─────────────────────────


class TestIdempotency:
    def test_duplicate_scope_while_inflight_returns_409(
        self, client, two_orgs, local_signer, archive_dir, db_session
    ):
        body = _valid_body()
        first = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert first.status_code == 202
        # Re-queue the first as still-queued so the second POST trips
        # the idempotency index (BackgroundTasks already ran it to
        # ready, which would otherwise let the second one through).
        job = (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == uuid.UUID(first.json()["id"]))
            .first()
        )
        job.status = "queued"
        db_session.commit()

        second = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert second.status_code == 409
        err = second.json()["error"]
        assert err["code"] == "export_already_inflight"
        assert err["existing_export_id"] == first.json()["id"]

    def test_completed_scope_does_not_block_new_request(
        self, client, two_orgs, local_signer, archive_dir
    ):
        body = _valid_body()
        first = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert first.status_code == 202
        second = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        # First build has already run to ready — second POST should
        # succeed, producing a fresh job.
        assert second.status_code == 202
        assert second.json()["id"] != first.json()["id"]


# ── Validation & authZ still enforced before state change ────────────


class TestValidationAndAuthz:
    def test_plain_member_gets_403(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": MEMBER_A_EMAIL},
        )
        assert resp.status_code == 403

    def test_cross_org_agent_id_is_400(self, client, two_orgs, local_signer, archive_dir):
        body = _valid_body(agent_ids=[str(two_orgs["agent_a"].id), str(two_orgs["agent_b"].id)])
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 400

    def test_reversed_period_is_422(self, client, two_orgs, local_signer, archive_dir):
        now = datetime.now(UTC)
        body = _valid_body(
            audit_period_start=now.isoformat(),
            audit_period_end=(now - timedelta(days=30)).isoformat(),
        )
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code in (400, 422)

    def test_period_over_max_is_rejected(self, client, two_orgs, local_signer, archive_dir):
        now = datetime.now(UTC)
        body = _valid_body(
            audit_period_start=(now - timedelta(days=600)).isoformat(),
            audit_period_end=now.isoformat(),
        )
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code in (400, 422)


# ── Tenancy on GET ───────────────────────────────────────────────────


class TestGetTenancy:
    def test_owner_gets_own_job(self, client, two_orgs, local_signer, archive_dir):
        created = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        got = client.get(
            f"/api/v1/exports/{created['id']}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert got.status_code == 200

    def test_other_org_gets_404_not_403(self, client, two_orgs, local_signer, archive_dir):
        created = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        got = client.get(
            f"/api/v1/exports/{created['id']}",
            headers={"X-API-Key": OWNER_B_EMAIL},
        )
        assert got.status_code == 404

    def test_platform_admin_can_fetch_any_org(self, client, two_orgs, local_signer, archive_dir):
        # Owner B creates a job in org B.
        created = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_B_EMAIL},
        ).json()
        # Platform admin (whose primary org is A) can still fetch it.
        got = client.get(
            f"/api/v1/exports/{created['id']}",
            headers={"X-API-Key": ADMIN_EMAIL},
        )
        assert got.status_code == 200
        assert got.json()["org_id"] == str(ORG_B_ID)


# ── List pagination ──────────────────────────────────────────────────


class TestList:
    def test_lists_own_org_only(self, client, two_orgs, local_signer, archive_dir):
        client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        client.post(
            "/api/v1/exports",
            json=_valid_body(
                audit_period_start=(datetime.now(UTC) - timedelta(days=60)).isoformat()
            ),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_B_EMAIL},
        )

        listed = client.get(
            "/api/v1/exports",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        assert len(listed["items"]) == 2
        assert all(item["org_id"] == str(ORG_A_ID) for item in listed["items"])

    def test_profile_filter(self, client, two_orgs, local_signer, archive_dir):
        client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        client.post(
            "/api/v1/exports",
            json=_valid_body(
                profile="eu_ai_act_2024",
                audit_period_start=(datetime.now(UTC) - timedelta(days=60)).isoformat(),
            ),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        listed = client.get(
            "/api/v1/exports?profile=soc2_tsc_2017",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        assert all(item["profile"] == "soc2_tsc_2017" for item in listed["items"])


# ── OpenAPI still reflects the surface ───────────────────────────────


class TestOpenAPI:
    def test_routes_present_with_correct_tag(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths", {})
        assert "/api/v1/exports" in paths
        assert "/api/v1/exports/{export_id}" in paths
        assert "/api/v1/exports/{export_id}/download" in paths
        post = paths["/api/v1/exports"]["post"]
        assert "compliance.exports" in post["tags"]
        # 202 is documented on the live endpoint.
        assert "202" in post["responses"]

    def test_profile_enum_in_schema(self, client):
        spec = client.get("/openapi.json").json()
        schemas = spec.get("components", {}).get("schemas", {})
        assert "ExportProfile" in schemas
        enum_values = schemas["ExportProfile"].get("enum", [])
        assert set(enum_values) >= {"soc2_tsc_2017", "eu_ai_act_2024", "nist_ai_rmf_1_0"}
