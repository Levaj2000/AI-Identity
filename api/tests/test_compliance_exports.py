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
        # Generic foundation check — the manifest must commit to every
        # artifact with a 64-hex sha256 and non-negative size. Profile-
        # specific artifact assertions live in the per-profile test
        # classes below. Uses SOC 2 since it's the most content-rich.
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        got = client.get(
            f"/api/v1/exports/{export_id}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        env = got["manifest_envelope"]
        manifest = json.loads(base64.b64decode(env["payload"]))
        paths = {a["path"] for a in manifest["artifacts"]}
        assert len(paths) > 0
        for artifact in manifest["artifacts"]:
            assert len(artifact["sha256"]) == 64
            assert artifact["bytes"] >= 0


# ── Download endpoint ────────────────────────────────────────────────


class TestDownload:
    def test_download_after_ready_returns_zip(self, client, two_orgs, local_signer, archive_dir):
        # Generic foundation check — download endpoint serves a real
        # zip with the manifest files, regardless of profile. Profile-
        # specific file-set assertions live in the per-profile classes.
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
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
        assert {"manifest.json", "manifest.dsse.json"} <= names

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


# ── SOC 2 profile end-to-end ─────────────────────────────────────────


class TestSoc2Profile:
    """End-to-end: POST soc2_tsc_2017 → builder dispatch → full artifact set."""

    def test_soc2_profile_produces_full_artifact_set(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 202
        export_id = resp.json()["id"]

        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert dl.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        names = set(zf.namelist())
        # SOC 2 set per docs/compliance/export-profiles.md §SOC 2.
        # attestations/ and policy_snapshots/ may be empty (no seeds
        # in this fixture), so we don't assert those directories.
        assert {
            "agent_inventory.csv",
            "access_log.csv",
            "change_log.csv",
            "control_results.csv",
            "chain_integrity.json",
            "evidence_summary.json",
            "manifest.json",
            "manifest.dsse.json",
        } <= names
        # Placeholder artifacts must NOT appear for soc2.
        assert "PLACEHOLDER.txt" not in names

    def test_soc2_evidence_summary_profile_field(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        summary = json.loads(zf.read("evidence_summary.json"))
        assert summary["profile"] == "soc2_tsc_2017"
        assert summary["scope"]["whole_org"] is True
        assert "artifact_control_mapping" in summary
        assert "SOC2-CC6.1" in summary["artifact_control_mapping"]["access_log.csv"]

    def test_soc2_manifest_commits_soc2_artifacts(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        got = client.get(
            f"/api/v1/exports/{resp.json()['id']}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        env = got["manifest_envelope"]
        manifest = json.loads(base64.b64decode(env["payload"]))
        paths = {a["path"] for a in manifest["artifacts"]}
        assert "access_log.csv" in paths
        assert "change_log.csv" in paths
        assert "control_results.csv" in paths
        assert "chain_integrity.json" in paths
        # Control tags round-trip through the manifest.
        access = next(a for a in manifest["artifacts"] if a["path"] == "access_log.csv")
        assert "SOC2-CC6.1" in access["controls"]


# ── EU AI Act profile end-to-end ─────────────────────────────────────


class TestEuAiActProfile:
    """End-to-end: POST eu_ai_act_2024 → builder dispatch → full artifact set."""

    def test_eu_ai_act_produces_full_artifact_set(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="eu_ai_act_2024"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 202
        export_id = resp.json()["id"]

        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert dl.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        names = set(zf.namelist())
        assert {
            "annex_iv_documentation.json",
            "access_log.csv",
            "chain_integrity.json",
            "human_oversight_log.csv",
            "agent_risk_classification.csv",
            "policy_change_log.csv",
            "capability_disclosures.csv",
            "agent_inventory.csv",
            "evidence_summary.json",
            "manifest.json",
            "manifest.dsse.json",
        } <= names
        # Placeholder must not leak into a real-profile bundle.
        assert "PLACEHOLDER.txt" not in names

    def test_eu_ai_act_summary_guardrail_flags_unclassified(
        self, client, two_orgs, local_signer, archive_dir
    ):
        # two_orgs seeds Agent A with default eu_ai_act_risk_class=null —
        # the summary's unclassified_agents count should therefore be ≥ 1.
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="eu_ai_act_2024"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        summary = json.loads(zf.read("evidence_summary.json"))
        assert summary["profile"] == "eu_ai_act_2024"
        assert summary["guardrail_facts"]["unclassified_agents"] >= 1

    def test_eu_ai_act_manifest_carries_article_controls(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="eu_ai_act_2024"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        got = client.get(
            f"/api/v1/exports/{resp.json()['id']}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        env = got["manifest_envelope"]
        manifest = json.loads(base64.b64decode(env["payload"]))
        access = next(a for a in manifest["artifacts"] if a["path"] == "access_log.csv")
        assert access["controls"] == ["EUAI-Art.12"]
        risk = next(
            a for a in manifest["artifacts"] if a["path"] == "agent_risk_classification.csv"
        )
        assert "EUAI-Art.6" in risk["controls"]


# ── Cost guardrails (rate limits + size cap + retention cleanup) ─────


class TestRateLimits:
    """POST rate limits per ADR-002."""

    def test_concurrent_limit_returns_429_with_retry_after(
        self, client, two_orgs, local_signer, archive_dir, monkeypatch, db_session
    ):
        from common.config.settings import settings

        # Squeeze the concurrent limit to 2 so the test doesn't have to
        # queue five real builds.
        monkeypatch.setattr(
            settings,
            "compliance_export_max_concurrent_per_org",
            2,
            raising=False,
        )
        # Queue two jobs and freeze them at queued so the third trips
        # the concurrent limit instead of the idempotency index.
        for period_days_ago in (10, 20):
            resp = client.post(
                "/api/v1/exports",
                json=_valid_body(
                    audit_period_start=(
                        datetime.now(UTC) - timedelta(days=30 + period_days_ago)
                    ).isoformat(),
                    audit_period_end=(
                        datetime.now(UTC) - timedelta(days=period_days_ago)
                    ).isoformat(),
                ),
                headers={"X-API-Key": OWNER_A_EMAIL},
            )
            job_id = uuid.UUID(resp.json()["id"])
            (
                db_session.query(ComplianceExport)
                .filter(ComplianceExport.id == job_id)
                .update({"status": "queued"})
            )
        db_session.commit()

        third = client.post(
            "/api/v1/exports",
            json=_valid_body(
                audit_period_start=(datetime.now(UTC) - timedelta(days=5)).isoformat(),
                audit_period_end=datetime.now(UTC).isoformat(),
            ),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "rate_limit_exceeded_concurrent"
        assert third.headers.get("Retry-After")

    def test_daily_limit_returns_429(
        self, client, two_orgs, local_signer, archive_dir, monkeypatch
    ):
        from common.config.settings import settings

        monkeypatch.setattr(settings, "compliance_export_max_per_day_per_org", 2, raising=False)
        # Three distinct scopes within the last 24h → third trips daily.
        now = datetime.now(UTC)
        for day_offset in range(3):
            resp = client.post(
                "/api/v1/exports",
                json=_valid_body(
                    audit_period_start=(now - timedelta(days=30 + day_offset)).isoformat(),
                    audit_period_end=(now - timedelta(days=day_offset)).isoformat(),
                ),
                headers={"X-API-Key": OWNER_A_EMAIL},
            )
            if day_offset < 2:
                assert resp.status_code == 202
            else:
                assert resp.status_code == 429
                assert resp.json()["error"]["code"] == "rate_limit_exceeded_daily"


class TestArchiveSizeCap:
    """10 GB archive cap per ADR-002."""

    def test_oversized_archive_fails_with_stable_error_code(
        self, client, two_orgs, local_signer, archive_dir, monkeypatch
    ):
        from common.config.settings import settings

        # 1 byte cap — anything the builder produces will blow through.
        monkeypatch.setattr(settings, "compliance_export_archive_bytes_cap", 1, raising=False)
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]

        got = client.get(
            f"/api/v1/exports/{export_id}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        body = got.json()
        assert body["status"] == "failed"
        assert body["error"]["code"] == "archive_too_large"
        # Archive file should have been deleted — download endpoint
        # 409s because the job is failed, not ready.
        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert dl.status_code == 409


class TestRetentionCleanup:
    """POST /api/internal/compliance-exports/cleanup."""

    def test_requires_internal_key(self, client, two_orgs):
        resp = client.post("/api/internal/compliance-exports/cleanup")
        assert resp.status_code == 401

    def test_dry_run_reports_candidates_without_deleting(
        self, client, two_orgs, local_signer, archive_dir, monkeypatch, db_session
    ):
        from common.config.settings import settings

        monkeypatch.setattr(settings, "internal_service_key", "test-internal-key", raising=False)
        # Build a real export, then age its completed_at past the cutoff.
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(resp.json()["id"])
        aged_completed = datetime.now(UTC) - timedelta(days=45)
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"completed_at": aged_completed})
        )
        db_session.commit()

        dry = client.post(
            "/api/internal/compliance-exports/cleanup?dry_run=true",
            headers={"x-internal-key": "test-internal-key"},
        )
        assert dry.status_code == 200
        body = dry.json()
        assert body["status"] == "dry_run"
        assert body["candidates"] == 1
        assert str(export_id) in body["candidate_ids"]
        assert body["archives_deleted"] == 0
        # Archive file still on disk after dry run.
        row = db_session.query(ComplianceExport).filter(ComplianceExport.id == export_id).first()
        assert row.archive_storage_path is not None

    def test_real_run_deletes_archive_and_clears_pointer(
        self, client, two_orgs, local_signer, archive_dir, monkeypatch, db_session
    ):
        import os

        from common.config.settings import settings

        monkeypatch.setattr(settings, "internal_service_key", "test-internal-key", raising=False)
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(resp.json()["id"])
        aged = datetime.now(UTC) - timedelta(days=45)
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"completed_at": aged})
        )
        db_session.commit()
        path_before = (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .first()
            .archive_storage_path
        )
        assert os.path.exists(path_before)

        real = client.post(
            "/api/internal/compliance-exports/cleanup?dry_run=false",
            headers={"x-internal-key": "test-internal-key"},
        )
        assert real.status_code == 200
        body = real.json()
        assert body["status"] == "ok"
        assert body["archives_deleted"] == 1
        assert body["rows_updated"] == 1

        # Archive file gone; download endpoint now returns 404.
        assert not os.path.exists(path_before)
        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert dl.status_code == 404

    def test_recent_jobs_are_not_candidates(
        self, client, two_orgs, local_signer, archive_dir, monkeypatch
    ):
        from common.config.settings import settings

        monkeypatch.setattr(settings, "internal_service_key", "test-internal-key", raising=False)
        # Fresh export, completed_at stays at "now" — well inside the
        # 30-day window.
        client.post(
            "/api/v1/exports",
            json=_valid_body(profile="soc2_tsc_2017"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )

        real = client.post(
            "/api/internal/compliance-exports/cleanup?dry_run=false",
            headers={"x-internal-key": "test-internal-key"},
        )
        assert real.status_code == 200
        assert real.json()["archives_deleted"] == 0


# ── Cancel endpoint ──────────────────────────────────────────────────


class TestCancelExport:
    """POST /api/v1/exports/{id}/cancel."""

    def test_cancel_queued_job_transitions_to_failed(
        self, client, two_orgs, local_signer, archive_dir, db_session
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(resp.json()["id"])
        # Force back to queued — the inline BackgroundTask would have
        # already completed it otherwise and cancel would be a no-op.
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"status": "queued"})
        )
        db_session.commit()

        cancel_resp = client.post(
            f"/api/v1/exports/{export_id}/cancel",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert cancel_resp.status_code == 200
        body = cancel_resp.json()
        assert body["status"] == "failed"
        assert body["error"]["code"] == "cancelled"
        assert "Cancelled by user" in body["error"]["message"]

    def test_cancel_ready_job_returns_409(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = resp.json()["id"]
        # BackgroundTask already ran to ready — cancel should 409.
        cancel_resp = client.post(
            f"/api/v1/exports/{export_id}/cancel",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert cancel_resp.status_code == 409
        assert cancel_resp.json()["error"]["code"] == "export_not_cancellable"

    def test_cancel_failed_job_returns_409(
        self, client, two_orgs, local_signer, archive_dir, db_session
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(resp.json()["id"])
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"status": "failed", "error_code": "test", "error_message": "x"})
        )
        db_session.commit()

        cancel_resp = client.post(
            f"/api/v1/exports/{export_id}/cancel",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert cancel_resp.status_code == 409

    def test_cancel_unknown_id_returns_404(self, client, two_orgs, local_signer, archive_dir):
        cancel_resp = client.post(
            f"/api/v1/exports/{uuid.uuid4()}/cancel",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert cancel_resp.status_code == 404

    def test_cancel_other_org_returns_404_not_403(
        self, client, two_orgs, local_signer, archive_dir, db_session
    ):
        # Owner A creates + freezes as queued
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(resp.json()["id"])
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"status": "queued"})
        )
        db_session.commit()

        # Owner B (different org) tries to cancel — 404, not 403
        other = client.post(
            f"/api/v1/exports/{export_id}/cancel",
            headers={"X-API-Key": OWNER_B_EMAIL},
        )
        assert other.status_code == 404

    def test_cancel_plain_member_returns_403(
        self, client, two_orgs, local_signer, archive_dir, db_session
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(resp.json()["id"])
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"status": "queued"})
        )
        db_session.commit()

        member_resp = client.post(
            f"/api/v1/exports/{export_id}/cancel",
            headers={"X-API-Key": MEMBER_A_EMAIL},
        )
        assert member_resp.status_code == 403

    def test_cancelled_scope_releases_idempotency_guard(
        self, client, two_orgs, local_signer, archive_dir, db_session
    ):
        """After cancel, a fresh POST for the same scope should succeed
        instead of 409'ing on the orphan. This is the user-visible win.
        """
        first = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        export_id = uuid.UUID(first.json()["id"])
        (
            db_session.query(ComplianceExport)
            .filter(ComplianceExport.id == export_id)
            .update({"status": "queued"})
        )
        db_session.commit()

        # Cancel + re-request with the same scope.
        client.post(
            f"/api/v1/exports/{export_id}/cancel",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        second = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert second.status_code == 202
        assert second.json()["id"] != str(export_id)


# ── NIST AI RMF profile end-to-end ───────────────────────────────────


class TestNistAiRmfProfile:
    """End-to-end: POST nist_ai_rmf_1_0 → builder dispatch → full artifact set."""

    def test_nist_produces_full_artifact_set(self, client, two_orgs, local_signer, archive_dir):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="nist_ai_rmf_1_0"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 202
        export_id = resp.json()["id"]
        dl = client.get(
            f"/api/v1/exports/{export_id}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert dl.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        names = set(zf.namelist())
        assert {
            "govern.json",
            "map.json",
            "measure_audit_log.csv",
            "measure_chain_integrity.json",
            "control_results.csv",
            "manage_approvals.csv",
            "manage_revocations.csv",
            "evidence_summary.json",
            "manifest.json",
            "manifest.dsse.json",
        } <= names
        # Placeholder artifacts must not leak into a real-profile bundle.
        assert "PLACEHOLDER.txt" not in names

    def test_nist_summary_carries_function_mapping(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="nist_ai_rmf_1_0"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        dl = client.get(
            f"/api/v1/exports/{resp.json()['id']}/download",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        zf = zipfile.ZipFile(io.BytesIO(dl.content))
        summary = json.loads(zf.read("evidence_summary.json"))
        assert summary["profile"] == "nist_ai_rmf_1_0"
        assert summary["framework_nature"] == "voluntary"
        assert "GOVERN" in summary["function_artifact_mapping"]
        assert "govern.json" in summary["function_artifact_mapping"]["GOVERN"]

    def test_nist_manifest_carries_function_controls(
        self, client, two_orgs, local_signer, archive_dir
    ):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(profile="nist_ai_rmf_1_0"),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        got = client.get(
            f"/api/v1/exports/{resp.json()['id']}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        ).json()
        env = got["manifest_envelope"]
        manifest = json.loads(base64.b64decode(env["payload"]))
        govern = next(a for a in manifest["artifacts"] if a["path"] == "govern.json")
        assert "NIST-GV-1.1" in govern["controls"]
        approvals = next(a for a in manifest["artifacts"] if a["path"] == "manage_approvals.csv")
        assert "NIST-MG-1.3" in approvals["controls"]


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
