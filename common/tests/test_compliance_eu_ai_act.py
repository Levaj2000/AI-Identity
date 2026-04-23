"""Unit tests for the EU AI Act 2024 profile builder.

Seeds a small org with agents (mixed risk classifications), audit
entries, an ApprovalRequest (Article 14 evidence), and a Policy,
then runs ``build_eu_ai_act_bundle`` directly and asserts on artifact
contents.
"""

from __future__ import annotations

import base64
import csv
import datetime
import hashlib
import io
import json
import uuid
import zipfile
from pathlib import Path  # noqa: TC003 — runtime use in _build_bundle

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.audit.writer import create_audit_entry
from common.compliance.builders.eu_ai_act import build_eu_ai_act_bundle
from common.compliance.bundle import ComplianceExportBundle
from common.forensic.signer import SignerHandle
from common.models import (
    Agent,
    ApprovalRequest,
    ForensicAttestation,
    Organization,
    OrgMembership,
    Policy,
    User,
)

# ── Seed data fixtures ───────────────────────────────────────────────


@pytest.fixture
def org_eu(db_session):
    """Org with three agents covering the risk-class spectrum:
    classified high-risk (4(a)), explicitly out-of-scope, and
    unclassified (null).
    """
    owner = User(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000e0"),
        email="eu-owner@example.test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(owner)
    db_session.flush()

    org = Organization(
        id=uuid.UUID("00000000-0000-0000-0000-00000000e0e0"),
        name="EU AI Act Test Org",
        owner_id=owner.id,
        tier="business",
    )
    db_session.add(org)
    db_session.flush()
    owner.org_id = org.id
    db_session.add(OrgMembership(org_id=org.id, user_id=owner.id, role="owner"))

    classified = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000e1"),
        user_id=owner.id,
        org_id=org.id,
        name="HR Screening Bot",
        description="Scores candidate applications for an initial triage.",
        status="active",
        capabilities=["chat_completion", "classification"],
        metadata_={},
        eu_ai_act_risk_class="4(a)",
    )
    out_of_scope = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000e2"),
        user_id=owner.id,
        org_id=org.id,
        name="Internal Doc Search",
        description="Internal-use-only doc search. Not an Annex III system.",
        status="active",
        capabilities=["search"],
        metadata_={},
        eu_ai_act_risk_class="not_in_scope",
    )
    unclassified = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000e3"),
        user_id=owner.id,
        org_id=org.id,
        name="Unclassified Agent",
        description="Not yet evaluated against Annex III.",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add_all([classified, out_of_scope, unclassified])
    db_session.commit()
    return {
        "owner": owner,
        "org": org,
        "classified": classified,
        "out_of_scope": out_of_scope,
        "unclassified": unclassified,
    }


def _seed_audit(db_session, org_eu, monkeypatch):
    from common.config.settings import settings

    monkeypatch.setattr(settings, "audit_hmac_key", "eu-test-hmac", raising=False)
    create_audit_entry(
        db_session,
        agent_id=org_eu["classified"].id,
        endpoint="/v1/chat/completions",
        method="POST",
        decision="allowed",
        user_id=org_eu["owner"].id,
        request_metadata={"correlation_id": "req-eu-1"},
    )
    create_audit_entry(
        db_session,
        agent_id=org_eu["out_of_scope"].id,
        endpoint="/v1/search",
        method="POST",
        decision="allowed",
        user_id=org_eu["owner"].id,
        request_metadata={"correlation_id": "req-eu-2"},
    )
    db_session.commit()


def _seed_approval(db_session, org_eu):
    """One resolved approval — Article 14 evidence."""
    now = datetime.datetime.now(tz=datetime.UTC)
    req = ApprovalRequest(
        id=uuid.UUID("00000000-0000-0000-0000-00000000aa01"),
        agent_id=org_eu["classified"].id,
        user_id=org_eu["owner"].id,
        endpoint="/v1/chat/completions",
        method="POST",
        request_metadata={"prompt_excerpt": "redacted"},
        status="approved",
        reviewer_id=org_eu["owner"].id,
        reviewer_note="Manual review — screening candidate profile",
        resolved_at=now - datetime.timedelta(days=1),
        expires_at=now + datetime.timedelta(hours=1),
        created_at=now - datetime.timedelta(days=1, hours=1),
    )
    db_session.add(req)
    db_session.commit()
    return req


def _seed_policy(db_session, org_eu):
    now = datetime.datetime.now(tz=datetime.UTC)
    policy = Policy(
        agent_id=org_eu["classified"].id,
        rules={"require_approval": [{"endpoint": "/v1/*"}]},
        version=3,
        is_active=True,
        created_at=now - datetime.timedelta(days=20),
        updated_at=now - datetime.timedelta(days=4),
    )
    db_session.add(policy)
    db_session.commit()
    return policy


def _seed_attestation(db_session, org_eu):
    now = datetime.datetime.now(tz=datetime.UTC)
    att = ForensicAttestation(
        id=uuid.uuid4(),
        org_id=org_eu["org"].id,
        session_id=uuid.UUID("00000000-0000-0000-0000-000000beef22"),
        first_audit_id=1,
        last_audit_id=2,
        event_count=2,
        audit_log_ids=[1, 2],
        session_start=now - datetime.timedelta(days=3),
        session_end=now - datetime.timedelta(days=3, hours=-1),
        signer_key_id="local:test",
        signed_at=now - datetime.timedelta(days=3, hours=-1),
        envelope={
            "payloadType": "application/vnd.ai-identity.attestation+json",
            "payload": "eyJldSI6ICJhdWRpdCJ9",
            "signatures": [{"keyid": "local:test", "sig": "YWJjZA=="}],
        },
    )
    db_session.add(att)
    db_session.commit()
    return att


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


def _build_bundle(tmp_path: Path, db_session, org_eu, *, agent_ids=None):
    now = datetime.datetime.now(tz=datetime.UTC)
    period_start = now - datetime.timedelta(days=30)
    period_end = now + datetime.timedelta(days=1)

    bundle = ComplianceExportBundle.create(tmp_path / "eu.zip", export_id=uuid.uuid4())
    build_eu_ai_act_bundle(
        bundle,
        db=db_session,
        org_id=org_eu["org"].id,
        export_id=bundle.export_id,
        audit_period_start=period_start,
        audit_period_end=period_end,
        built_at=now,
        agent_ids=agent_ids,
    )
    signer, _ = _local_signer()
    bundle.seal(
        profile="eu_ai_act_2024",
        audit_period_start=period_start,
        audit_period_end=period_end,
        built_at=now,
        org_id=org_eu["org"].id,
        signer=signer,
    )
    return bundle


def _read_csv(zf: zipfile.ZipFile, path: str) -> list[dict]:
    with zf.open(path) as fp:
        text = io.TextIOWrapper(fp, encoding="utf-8")
        return list(csv.DictReader(text))


# ── Tests ────────────────────────────────────────────────────────────


class TestArtifactsPresent:
    def test_every_required_eu_artifact_is_in_archive(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        _seed_approval(db_session, org_eu)
        _seed_policy(db_session, org_eu)
        _seed_attestation(db_session, org_eu)

        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            names = set(zf.namelist())
        assert "annex_iv_documentation.json" in names
        assert "access_log.csv" in names
        assert "chain_integrity.json" in names
        assert "human_oversight_log.csv" in names
        assert "agent_risk_classification.csv" in names
        assert "policy_change_log.csv" in names
        assert "capability_disclosures.csv" in names
        assert "agent_inventory.csv" in names
        assert "evidence_summary.json" in names
        assert any(n.startswith("attestations/") for n in names)


class TestAgentRiskClassification:
    def test_classified_agent_has_annex_iii_description(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "agent_risk_classification.csv")
        classified = next(r for r in rows if r["agent_id"] == str(org_eu["classified"].id))
        assert classified["annex_iii_code"] == "4(a)"
        assert "Recruitment" in classified["annex_iii_description"]
        assert classified["classification_status"] == "in_scope"

    def test_out_of_scope_agent_is_flagged_correctly(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "agent_risk_classification.csv")
        oos = next(r for r in rows if r["agent_id"] == str(org_eu["out_of_scope"].id))
        assert oos["annex_iii_code"] == "not_in_scope"
        assert oos["classification_status"] == "out_of_scope"

    def test_unclassified_agent_surfaces_explicitly(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "agent_risk_classification.csv")
            summary = json.loads(zf.read("evidence_summary.json"))
        unclassified = next(r for r in rows if r["agent_id"] == str(org_eu["unclassified"].id))
        assert unclassified["annex_iii_code"] == ""
        assert unclassified["classification_status"] == "unclassified"
        # Guardrail fact: count of unclassified agents surfaces honestly
        # in the summary so auditors know the classification is incomplete.
        assert summary["guardrail_facts"]["unclassified_agents"] == 1


class TestHumanOversightLog:
    def test_approval_row_serialized(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        _seed_approval(db_session, org_eu)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "human_oversight_log.csv")
        assert len(rows) == 1
        assert rows[0]["status"] == "approved"
        assert rows[0]["reviewer_note"].startswith("Manual review")
        assert rows[0]["resolved_at"]  # non-empty

    def test_empty_log_still_has_header(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            text = zf.read("human_oversight_log.csv").decode("utf-8")
        # Header row is present even when no approvals occurred.
        assert text.startswith("request_id,")


class TestPolicyChangeLog:
    def test_rules_sha256_is_deterministic(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        policy = _seed_policy(db_session, org_eu)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "policy_change_log.csv")
        assert len(rows) == 1
        expected_hash = hashlib.sha256(
            json.dumps(policy.rules, sort_keys=True).encode("utf-8")
        ).hexdigest()
        assert rows[0]["rules_sha256"] == expected_hash
        assert rows[0]["is_active"] == "true"


class TestCapabilityDisclosures:
    def test_capabilities_round_trip_as_json(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "capability_disclosures.csv")
        classified = next(r for r in rows if r["agent_id"] == str(org_eu["classified"].id))
        assert json.loads(classified["capabilities"]) == [
            "chat_completion",
            "classification",
        ]


class TestAnnexIvDocumentation:
    def test_annex_iv_per_agent_purpose_includes_each_agent(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            doc = json.loads(zf.read("annex_iv_documentation.json"))
        purposes = doc["annex_iv_sections"]["1(b)_intended_purpose_per_agent"]
        agent_ids = {p["agent_id"] for p in purposes}
        assert agent_ids == {
            str(org_eu["classified"].id),
            str(org_eu["out_of_scope"].id),
            str(org_eu["unclassified"].id),
        }

    def test_gaps_section_documents_art_10_and_gpai(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            doc = json.loads(zf.read("annex_iv_documentation.json"))
        topics = {gap["article"] for gap in doc["gaps_and_limitations"]}
        assert "Art. 10" in topics
        assert "Art. 51+" in topics


class TestEvidenceSummary:
    def test_summary_profile_and_applicability(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_eu)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            summary = json.loads(zf.read("evidence_summary.json"))
        assert summary["profile"] == "eu_ai_act_2024"
        assert "high-risk" in summary["scope"]["applicability"].lower()
        assert "EUAI-Art.12" in summary["artifact_control_mapping"]["access_log.csv"]
        assert "Art. 10" in " ".join(summary["known_gaps"])


class TestAgentScope:
    def test_agent_ids_narrows_every_artifact(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        _seed_approval(db_session, org_eu)
        _seed_policy(db_session, org_eu)

        bundle = _build_bundle(tmp_path, db_session, org_eu, agent_ids=[org_eu["classified"].id])
        with zipfile.ZipFile(bundle.archive_path) as zf:
            inventory = _read_csv(zf, "agent_inventory.csv")
            access = _read_csv(zf, "access_log.csv")
            approvals = _read_csv(zf, "human_oversight_log.csv")
            policy = _read_csv(zf, "policy_change_log.csv")
        for rows in (inventory, access, approvals, policy):
            for row in rows:
                assert row["agent_id"] == str(org_eu["classified"].id)


class TestDeterminism:
    def test_same_inputs_produce_identical_artifact_bytes(
        self, db_session, org_eu, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_eu, monkeypatch)
        _seed_approval(db_session, org_eu)
        _seed_policy(db_session, org_eu)
        _seed_attestation(db_session, org_eu)

        a = _build_bundle(tmp_path / "a", db_session, org_eu)
        b = _build_bundle(tmp_path / "b", db_session, org_eu)
        artifacts = [
            "agent_inventory.csv",
            "access_log.csv",
            "agent_risk_classification.csv",
            "capability_disclosures.csv",
            "policy_change_log.csv",
            "human_oversight_log.csv",
        ]
        with (
            zipfile.ZipFile(a.archive_path) as za,
            zipfile.ZipFile(b.archive_path) as zb,
        ):
            for name in artifacts:
                assert za.read(name) == zb.read(name), f"{name} diverged"


class TestManifestCommits:
    def test_manifest_covers_every_artifact(self, db_session, org_eu, monkeypatch, tmp_path):
        _seed_audit(db_session, org_eu, monkeypatch)
        _seed_approval(db_session, org_eu)
        _seed_policy(db_session, org_eu)
        _seed_attestation(db_session, org_eu)

        bundle = _build_bundle(tmp_path, db_session, org_eu)
        env = bundle.manifest_envelope
        manifest = json.loads(base64.b64decode(env.payload))
        manifest_paths = {a["path"] for a in manifest["artifacts"]}

        with zipfile.ZipFile(bundle.archive_path) as zf:
            archive_paths = set(zf.namelist()) - {"manifest.json", "manifest.dsse.json"}
        assert archive_paths == manifest_paths
