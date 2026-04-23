"""Unit tests for the NIST AI RMF 1.0 profile builder."""

from __future__ import annotations

import csv
import datetime
import io
import json
import uuid
import zipfile
from pathlib import Path  # noqa: TC003 — runtime use in _build_bundle

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.audit.writer import create_audit_entry
from common.compliance.builders.nist_ai_rmf import build_nist_ai_rmf_bundle
from common.compliance.bundle import ComplianceExportBundle
from common.forensic.signer import SignerHandle
from common.models import (
    Agent,
    ApprovalRequest,
    ComplianceCheck,
    ComplianceFramework,
    ComplianceReport,
    ComplianceResult,
    Organization,
    OrgMembership,
    Policy,
    User,
)

# ── Seed fixtures ────────────────────────────────────────────────────


@pytest.fixture
def org_nist(db_session):
    """Org with an owner, a member, two agents (one later revoked)."""
    owner = User(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000f0"),
        email="nist-owner@example.test",
        role="owner",
        tier="enterprise",
    )
    member = User(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000f1"),
        email="nist-member@example.test",
        role="owner",
        tier="enterprise",
    )
    db_session.add_all([owner, member])
    db_session.flush()

    org = Organization(
        id=uuid.UUID("00000000-0000-0000-0000-00000000f0f0"),
        name="NIST Test Org",
        owner_id=owner.id,
        tier="business",
    )
    db_session.add(org)
    db_session.flush()
    owner.org_id = org.id
    member.org_id = org.id
    db_session.add_all(
        [
            OrgMembership(org_id=org.id, user_id=owner.id, role="owner"),
            OrgMembership(org_id=org.id, user_id=member.id, role="member"),
        ]
    )

    active = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000f2"),
        user_id=owner.id,
        org_id=org.id,
        name="Active Agent",
        description="Primary production agent",
        status="active",
        capabilities=["chat_completion"],
        metadata_={},
        eu_ai_act_risk_class="4(b)",
    )
    revoked = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000f3"),
        user_id=owner.id,
        org_id=org.id,
        name="Revoked Agent",
        description="Retired — identity compromise remediation",
        status="revoked",
        capabilities=[],
        metadata_={},
        revoked_at=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=5),
    )
    db_session.add_all([active, revoked])
    db_session.commit()
    return {
        "owner": owner,
        "member": member,
        "org": org,
        "active": active,
        "revoked": revoked,
    }


def _seed_policy(db_session, org_nist):
    now = datetime.datetime.now(tz=datetime.UTC)
    p = Policy(
        agent_id=org_nist["active"].id,
        rules={"deny": [{"endpoint": "/admin/*"}]},
        version=2,
        is_active=True,
        created_at=now - datetime.timedelta(days=15),
        updated_at=now - datetime.timedelta(days=4),
    )
    db_session.add(p)
    db_session.commit()
    return p


def _seed_audit(db_session, org_nist, monkeypatch):
    from common.config.settings import settings

    monkeypatch.setattr(settings, "audit_hmac_key", "nist-test-hmac", raising=False)
    create_audit_entry(
        db_session,
        agent_id=org_nist["active"].id,
        endpoint="/v1/chat/completions",
        method="POST",
        decision="allowed",
        user_id=org_nist["owner"].id,
        request_metadata={"correlation_id": "nist-r1"},
    )
    # Key revocation event — surfaces in manage_revocations.csv.
    create_audit_entry(
        db_session,
        agent_id=org_nist["active"].id,
        endpoint=f"/api/v1/agents/{org_nist['active'].id}/keys/1",
        method="DELETE",
        decision="allowed",
        user_id=org_nist["owner"].id,
        request_metadata={
            "action_type": "key_revoked",
            "resource_type": "agent_key",
            "agent_name": "Active Agent",
        },
    )
    db_session.commit()


def _seed_approval(db_session, org_nist):
    now = datetime.datetime.now(tz=datetime.UTC)
    req = ApprovalRequest(
        id=uuid.UUID("00000000-0000-0000-0000-00000000ff01"),
        agent_id=org_nist["active"].id,
        user_id=org_nist["owner"].id,
        endpoint="/v1/sensitive",
        method="POST",
        request_metadata={},
        status="approved",
        reviewer_id=org_nist["owner"].id,
        reviewer_note="Confirmed consent from subject",
        resolved_at=now - datetime.timedelta(hours=6),
        expires_at=now + datetime.timedelta(hours=1),
        created_at=now - datetime.timedelta(hours=7),
    )
    db_session.add(req)
    db_session.commit()
    return req


def _seed_control_result(db_session, org_nist):
    fw = ComplianceFramework(name="NIST AI RMF", version="1.0")
    db_session.add(fw)
    db_session.flush()
    check = ComplianceCheck(
        framework_id=fw.id,
        code="NIST-MS-4.1",
        name="Post-deployment monitoring",
        severity="high",
        category="governance",
        check_type="automated",
    )
    db_session.add(check)
    db_session.flush()
    report = ComplianceReport(
        user_id=org_nist["owner"].id,
        framework_id=fw.id,
        status="completed",
        score=88.0,
        created_at=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=2),
    )
    db_session.add(report)
    db_session.flush()
    db_session.add(
        ComplianceResult(
            report_id=report.id,
            check_id=check.id,
            status="pass",
            evidence={"audit_rows": 42},
        )
    )
    db_session.commit()


# ── Signer + bundle helper ───────────────────────────────────────────


def _local_signer() -> tuple[SignerHandle, bytes]:
    pk = ec.generate_private_key(ec.SECP256R1())

    def sign(message: bytes) -> bytes:
        return pk.sign(message, ec.ECDSA(hashes.SHA256()))

    public_pem = pk.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return SignerHandle(sign=sign, key_id="local:test", backend="local"), public_pem


def _build_bundle(tmp_path: Path, db_session, org_nist, *, agent_ids=None):
    now = datetime.datetime.now(tz=datetime.UTC)
    period_start = now - datetime.timedelta(days=30)
    period_end = now + datetime.timedelta(days=1)

    bundle = ComplianceExportBundle.create(tmp_path / "nist.zip", export_id=uuid.uuid4())
    build_nist_ai_rmf_bundle(
        bundle,
        db=db_session,
        org_id=org_nist["org"].id,
        export_id=bundle.export_id,
        audit_period_start=period_start,
        audit_period_end=period_end,
        built_at=now,
        agent_ids=agent_ids,
    )
    signer, _ = _local_signer()
    bundle.seal(
        profile="nist_ai_rmf_1_0",
        audit_period_start=period_start,
        audit_period_end=period_end,
        built_at=now,
        org_id=org_nist["org"].id,
        signer=signer,
    )
    return bundle


def _read_csv(zf: zipfile.ZipFile, path: str) -> list[dict]:
    with zf.open(path) as fp:
        text = io.TextIOWrapper(fp, encoding="utf-8")
        return list(csv.DictReader(text))


# ── Tests ────────────────────────────────────────────────────────────


class TestArtifactsPresent:
    def test_every_required_nist_artifact_is_in_archive(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        _seed_policy(db_session, org_nist)
        _seed_audit(db_session, org_nist, monkeypatch)
        _seed_approval(db_session, org_nist)
        _seed_control_result(db_session, org_nist)

        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            names = set(zf.namelist())
        assert "govern.json" in names
        assert "map.json" in names
        assert "measure_audit_log.csv" in names
        assert "measure_chain_integrity.json" in names
        assert "control_results.csv" in names
        assert "manage_approvals.csv" in names
        assert "manage_revocations.csv" in names
        assert "evidence_summary.json" in names


class TestGovern:
    def test_govern_has_policy_catalog_role_assignments_and_bindings(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        _seed_policy(db_session, org_nist)
        _seed_audit(db_session, org_nist, monkeypatch)

        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            govern = json.loads(zf.read("govern.json"))

        assert govern["function"] == "GOVERN"
        assert len(govern["policy_catalog"]) == 1
        assert govern["policy_catalog"][0]["rules_sha256"]
        # Role assignments include both owner and member roles.
        roles = {ra["role"] for ra in govern["role_assignments"]}
        assert roles == {"owner", "member"}
        # Active policy is bound to the active agent.
        bindings = govern["agent_policy_bindings"]
        assert len(bindings) == 1
        assert bindings[0]["agent_id"] == str(org_nist["active"].id)


class TestMap:
    def test_map_classifies_agents_with_risk_status(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_nist, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            map_doc = json.loads(zf.read("map.json"))
        by_id = {a["agent_id"]: a for a in map_doc["agents"]}
        active = by_id[str(org_nist["active"].id)]
        revoked = by_id[str(org_nist["revoked"].id)]
        assert active["risk_classification"]["code"] == "4(b)"
        assert active["risk_classification"]["status"] == "in_scope"
        # Revoked agent has no risk class set — should come through as unclassified.
        assert revoked["risk_classification"]["status"] == "unclassified"
        # Limitations section names the known model-level gaps.
        gaps = " ".join(map_doc["limitations"])
        assert "MP-5.1" in gaps or "impact" in gaps.lower()


class TestMeasureAuditLog:
    def test_audit_log_has_hmac_fields(self, db_session, org_nist, monkeypatch, tmp_path):
        _seed_audit(db_session, org_nist, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "measure_audit_log.csv")
        assert len(rows) == 2
        for row in rows:
            assert len(row["entry_hash"]) == 64


class TestManageApprovals:
    def test_approval_serializes(self, db_session, org_nist, monkeypatch, tmp_path):
        _seed_audit(db_session, org_nist, monkeypatch)
        _seed_approval(db_session, org_nist)
        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "manage_approvals.csv")
        assert len(rows) == 1
        assert rows[0]["status"] == "approved"


class TestManageRevocations:
    def test_revocations_combine_agent_and_key_sources(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_nist, monkeypatch)  # includes key_revoked
        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "manage_revocations.csv")
        # At least one agent revocation (from fixture) and one key
        # revocation (from _seed_audit). Sources should be distinct.
        sources = {r["source"] for r in rows}
        assert "agents.revoked_at" in sources
        assert "audit_log" in sources

    def test_revocations_empty_when_nothing_revoked(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        # No audit seed, no key revocations. Agent fixture has a revoked
        # agent though; adjust period to exclude it.
        now = datetime.datetime.now(tz=datetime.UTC)
        period_start = now + datetime.timedelta(days=30)  # future window
        period_end = now + datetime.timedelta(days=31)

        bundle = ComplianceExportBundle.create(tmp_path / "empty.zip", export_id=uuid.uuid4())
        build_nist_ai_rmf_bundle(
            bundle,
            db=db_session,
            org_id=org_nist["org"].id,
            export_id=bundle.export_id,
            audit_period_start=period_start,
            audit_period_end=period_end,
            built_at=now,
            agent_ids=None,
        )
        signer, _ = _local_signer()
        bundle.seal(
            profile="nist_ai_rmf_1_0",
            audit_period_start=period_start,
            audit_period_end=period_end,
            built_at=now,
            org_id=org_nist["org"].id,
            signer=signer,
        )
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "manage_revocations.csv")
        assert rows == []


class TestEvidenceSummary:
    def test_summary_declares_voluntary_nature(self, db_session, org_nist, monkeypatch, tmp_path):
        _seed_audit(db_session, org_nist, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_nist)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            summary = json.loads(zf.read("evidence_summary.json"))
        assert summary["profile"] == "nist_ai_rmf_1_0"
        assert summary["framework_nature"] == "voluntary"
        assert set(summary["function_artifact_mapping"].keys()) == {
            "GOVERN",
            "MAP",
            "MEASURE",
            "MANAGE",
        }
        # Every listed artifact for MEASURE must be in the archive.
        with zipfile.ZipFile(bundle.archive_path) as zf:
            names = set(zf.namelist())
        for artifact in summary["function_artifact_mapping"]["MEASURE"]:
            if artifact.endswith("/*.dsse.json"):
                continue  # glob — may legitimately be empty
            assert artifact in names


class TestAgentScope:
    def test_agent_ids_narrows_measure_and_manage(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        _seed_policy(db_session, org_nist)
        _seed_audit(db_session, org_nist, monkeypatch)
        _seed_approval(db_session, org_nist)

        bundle = _build_bundle(tmp_path, db_session, org_nist, agent_ids=[org_nist["active"].id])
        with zipfile.ZipFile(bundle.archive_path) as zf:
            audit = _read_csv(zf, "measure_audit_log.csv")
            approvals = _read_csv(zf, "manage_approvals.csv")
            map_doc = json.loads(zf.read("map.json"))
        assert {row["agent_id"] for row in audit} == {str(org_nist["active"].id)}
        assert {row["agent_id"] for row in approvals} == {str(org_nist["active"].id)}
        assert len(map_doc["agents"]) == 1


class TestDeterminism:
    def test_same_inputs_produce_identical_artifacts(
        self, db_session, org_nist, monkeypatch, tmp_path
    ):
        _seed_policy(db_session, org_nist)
        _seed_audit(db_session, org_nist, monkeypatch)
        _seed_approval(db_session, org_nist)

        a = _build_bundle(tmp_path / "a", db_session, org_nist)
        b = _build_bundle(tmp_path / "b", db_session, org_nist)
        artifacts = [
            "govern.json",
            "map.json",
            "measure_audit_log.csv",
            "manage_approvals.csv",
            "manage_revocations.csv",
        ]
        with (
            zipfile.ZipFile(a.archive_path) as za,
            zipfile.ZipFile(b.archive_path) as zb,
        ):
            for name in artifacts:
                assert za.read(name) == zb.read(name), f"{name} diverged"
