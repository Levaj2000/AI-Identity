"""Unit tests for the SOC 2 profile builder.

Seeds a small org with agents, audit entries, attestations, a
compliance report, and a policy snapshot, then runs
``build_soc2_bundle`` directly and asserts on artifact contents.
Skips HTTP so failures point at the builder rather than router glue.
"""

from __future__ import annotations

import base64
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
from common.compliance.builders.soc2 import build_soc2_bundle
from common.compliance.bundle import ComplianceExportBundle
from common.forensic.signer import SignerHandle
from common.models import (
    Agent,
    ComplianceCheck,
    ComplianceFramework,
    ComplianceReport,
    ComplianceResult,
    ForensicAttestation,
    Organization,
    OrgMembership,
    Policy,
    User,
)

# ── Seed data fixtures ───────────────────────────────────────────────


@pytest.fixture
def org_a(db_session):
    """One org with an owner, two agents (one revoked), and some
    audit activity spanning the full SOC 2 evidence surface.
    """
    owner = User(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000a0"),
        email="soc2-owner@example.test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(owner)
    db_session.flush()

    org = Organization(
        id=uuid.UUID("00000000-0000-0000-0000-00000000a0a0"),
        name="SOC 2 Test Org",
        owner_id=owner.id,
        tier="business",
    )
    db_session.add(org)
    db_session.flush()
    owner.org_id = org.id
    db_session.add(OrgMembership(org_id=org.id, user_id=owner.id, role="owner"))

    agent_active = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000a1"),
        user_id=owner.id,
        org_id=org.id,
        name="Active Agent",
        status="active",
        capabilities=["chat_completion"],
        metadata_={},
        eu_ai_act_risk_class="4(b)",
    )
    agent_revoked = Agent(
        id=uuid.UUID("00000000-0000-0000-0000-0000000000a2"),
        user_id=owner.id,
        org_id=org.id,
        name="Revoked Agent",
        status="revoked",
        capabilities=[],
        metadata_={},
        revoked_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC),
    )
    db_session.add_all([agent_active, agent_revoked])
    db_session.commit()
    return {
        "owner": owner,
        "org": org,
        "active": agent_active,
        "revoked": agent_revoked,
    }


def _seed_audit(db_session, org_a, monkeypatch):
    """Insert a mix of request events and lifecycle events."""
    # create_audit_entry looks up agent.org_id internally; monkeypatch
    # the HMAC key to a deterministic value for this test.
    from common.config.settings import settings

    monkeypatch.setattr(settings, "audit_hmac_key", "soc2-test-hmac-key", raising=False)

    # Two request events (CC6.1/CC7.2).
    create_audit_entry(
        db_session,
        agent_id=org_a["active"].id,
        endpoint="/v1/chat/completions",
        method="POST",
        decision="allowed",
        user_id=org_a["owner"].id,
        request_metadata={"correlation_id": "req-1", "policy_version": "1"},
    )
    create_audit_entry(
        db_session,
        agent_id=org_a["active"].id,
        endpoint="/v1/chat/completions",
        method="POST",
        decision="denied",
        user_id=org_a["owner"].id,
        request_metadata={"correlation_id": "req-2"},
    )

    # Two lifecycle events (CC6.2/CC6.6/CC8.1).
    create_audit_entry(
        db_session,
        agent_id=org_a["active"].id,
        endpoint=f"/api/v1/agents/{org_a['active'].id}",
        method="PUT",
        decision="allowed",
        user_id=org_a["owner"].id,
        request_metadata={
            "action_type": "agent_updated",
            "resource_type": "agent",
            "agent_name": "Active Agent",
        },
    )
    create_audit_entry(
        db_session,
        agent_id=org_a["revoked"].id,
        endpoint=f"/api/v1/agents/{org_a['revoked'].id}",
        method="DELETE",
        decision="allowed",
        user_id=org_a["owner"].id,
        request_metadata={
            "action_type": "agent_revoked",
            "resource_type": "agent",
            "agent_name": "Revoked Agent",
        },
    )
    db_session.commit()


def _seed_attestation(db_session, org_a):
    """One forensic attestation inside the audit period.

    Timestamps are anchored to "now" so the attestation lands inside
    the default _build_bundle test period (now ± 30 days).
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    att = ForensicAttestation(
        id=uuid.uuid4(),
        org_id=org_a["org"].id,
        session_id=uuid.UUID("00000000-0000-0000-0000-0000000beef1"),
        first_audit_id=1,
        last_audit_id=4,
        event_count=4,
        audit_log_ids=[1, 2, 3, 4],
        session_start=now - datetime.timedelta(days=7),
        session_end=now - datetime.timedelta(days=7, hours=-1),
        signer_key_id="local:test",
        signed_at=now - datetime.timedelta(days=7, hours=-1),
        envelope={
            "payloadType": "application/vnd.ai-identity.attestation+json",
            "payload": "eyJoZWxsbyI6ICJhdWRpdG9yIn0=",
            "signatures": [{"keyid": "local:test", "sig": "YWJjZA=="}],
        },
    )
    db_session.add(att)
    db_session.commit()
    return att


def _seed_control_results(db_session, org_a):
    """A compliance report with two check results."""
    framework = ComplianceFramework(name="SOC 2 TSC", version="2017")
    db_session.add(framework)
    db_session.flush()
    check_a = ComplianceCheck(
        framework_id=framework.id,
        code="SOC2-CC6.1",
        name="Logical access",
        severity="high",
        category="security",
        check_type="automated",
    )
    check_b = ComplianceCheck(
        framework_id=framework.id,
        code="SOC2-CC7.2",
        name="Monitoring",
        severity="high",
        category="security",
        check_type="automated",
    )
    db_session.add_all([check_a, check_b])
    db_session.flush()

    report = ComplianceReport(
        user_id=org_a["owner"].id,
        framework_id=framework.id,
        status="completed",
        score=92.5,
        created_at=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=3),
    )
    db_session.add(report)
    db_session.flush()

    db_session.add_all(
        [
            ComplianceResult(
                report_id=report.id,
                check_id=check_a.id,
                status="pass",
                evidence={"policy_count": 2},
            ),
            ComplianceResult(
                report_id=report.id,
                check_id=check_b.id,
                status="warning",
                evidence={"incidents": 0},
                remediation="Investigate soft-warning signal in Q2",
            ),
        ]
    )
    db_session.commit()
    return report


def _seed_policy(db_session, org_a):
    """A policy row updated inside the audit period."""
    now = datetime.datetime.now(tz=datetime.UTC)
    policy = Policy(
        agent_id=org_a["active"].id,
        rules={"deny": [{"endpoint": "/admin/*"}]},
        version=2,
        is_active=True,
        created_at=now - datetime.timedelta(days=25),
        updated_at=now - datetime.timedelta(days=5),
    )
    db_session.add(policy)
    db_session.commit()
    return policy


# ── Signer ──────────────────────────────────────────────────────────


def _local_signer() -> tuple[SignerHandle, bytes]:
    pk = ec.generate_private_key(ec.SECP256R1())

    def sign(message: bytes) -> bytes:
        return pk.sign(message, ec.ECDSA(hashes.SHA256()))

    public_pem = pk.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return SignerHandle(sign=sign, key_id="local:test", backend="local"), public_pem


def _build_bundle(
    tmp_path: Path,
    db_session,
    org_a,
    *,
    agent_ids=None,
    period_start=None,
    period_end=None,
):
    # Default the period to "now ± 30 days" so rows created by the
    # live audit writer (which stamps created_at = now) always land
    # inside it. Tests that want to exercise out-of-range exclusion
    # override explicitly.
    now = datetime.datetime.now(tz=datetime.UTC)
    default_start = now - datetime.timedelta(days=30)
    default_end = now + datetime.timedelta(days=1)
    period_start = period_start or default_start
    period_end = period_end or default_end
    built_at = now

    bundle = ComplianceExportBundle.create(tmp_path / "soc2.zip", export_id=uuid.uuid4())
    signer, _ = _local_signer()
    build_soc2_bundle(
        bundle,
        db=db_session,
        org_id=org_a["org"].id,
        export_id=bundle.export_id,
        audit_period_start=period_start,
        audit_period_end=period_end,
        built_at=built_at,
        agent_ids=agent_ids,
        signer=signer,
    )
    bundle.seal(
        profile="soc2_tsc_2017",
        audit_period_start=period_start,
        audit_period_end=period_end,
        built_at=built_at,
        org_id=org_a["org"].id,
        signer=signer,
    )
    return bundle


def _read_csv(zf: zipfile.ZipFile, path: str) -> list[dict]:
    with zf.open(path) as fp:
        text = io.TextIOWrapper(fp, encoding="utf-8")
        return list(csv.DictReader(text))


# ── Tests ────────────────────────────────────────────────────────────


class TestArtifactsPresent:
    def test_every_required_soc2_artifact_is_in_archive(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        _seed_attestation(db_session, org_a)
        _seed_control_results(db_session, org_a)
        _seed_policy(db_session, org_a)

        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            names = set(zf.namelist())
        assert "agent_inventory.csv" in names
        assert "access_log.csv" in names
        assert "change_log.csv" in names
        assert "chain_integrity.json" in names
        assert "control_results.csv" in names
        assert "evidence_summary.json" in names
        assert "manifest.json" in names
        assert "manifest.dsse.json" in names
        # Attestation file lands under attestations/
        assert any(n.startswith("attestations/") for n in names)
        # Policy snapshot under policy_snapshots/
        assert any(n.startswith("policy_snapshots/") for n in names)


class TestAgentInventory:
    def test_inventory_includes_active_and_revoked(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "agent_inventory.csv")
        statuses = {r["status"] for r in rows}
        assert statuses == {"active", "revoked"}
        # Revoked agent carries revoked_at; active does not.
        active = next(r for r in rows if r["status"] == "active")
        revoked = next(r for r in rows if r["status"] == "revoked")
        assert active["revoked_at"] == ""
        assert revoked["revoked_at"].startswith("2026-02-01")
        # eu_ai_act_risk_class round-trips for the classified agent.
        assert active["eu_ai_act_risk_class"] == "4(b)"


class TestAccessLog:
    def test_access_log_has_every_audit_row_in_period(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "access_log.csv")
        # _seed_audit inserts 4 rows — all fall inside the default test period.
        assert len(rows) == 4

    def test_access_log_hmac_fields_populated(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "access_log.csv")
        for row in rows:
            # Hashes are 64-char hex.
            assert len(row["entry_hash"]) == 64
            assert row["prev_hash"]  # non-empty (GENESIS or prior hash)

    def test_access_log_period_filter_excludes_out_of_range_rows(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        # Period in the far future — nothing should match.
        bundle = _build_bundle(
            tmp_path,
            db_session,
            org_a,
            period_start=datetime.datetime(2099, 1, 1, tzinfo=datetime.UTC),
            period_end=datetime.datetime(2099, 12, 31, tzinfo=datetime.UTC),
        )
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "access_log.csv")
        assert rows == []


class TestChangeLog:
    def test_change_log_contains_lifecycle_actions_only(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "change_log.csv")
        actions = {r["action_type"] for r in rows}
        assert actions == {"agent_updated", "agent_revoked"}
        # Non-lifecycle POST /v1/chat/completions rows must not leak in.
        for row in rows:
            assert row["action_type"] in {"agent_updated", "agent_revoked"}

    def test_change_log_v2_columns_present(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with (
            zipfile.ZipFile(bundle.archive_path) as zf,
            zf.open("change_log.csv") as fp,
        ):
            text = io.TextIOWrapper(fp, encoding="utf-8")
            reader = csv.DictReader(text)
            header = list(reader.fieldnames or [])
        # The v2 column set is contractual — reviewers should see this
        # fail loudly if columns are reordered or dropped.
        assert header == [
            "audit_log_id",
            "created_at",
            "action_type",
            "resource_type",
            "agent_id",
            "agent_name",
            "actor_user_id",
            "actor_email",
            "actor_principal",
            "actor_type",
            "decision",
            "decision_reason",
            "policy_version",
            "ip_address",
            "user_agent",
            "session_id",
            "request_id",
            "correlation_id",
            "key_prefix",
            "key_type",
            "grace_hours",
            "old_status",
            "new_status",
            "diff_json",
            "details_json",
            "entry_hash",
            "prev_hash",
            "signature",
            "signing_key_id",
            "chain_segment",
        ]

    def test_change_log_hmac_hashes_populated(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "change_log.csv")
        for row in rows:
            assert len(row["entry_hash"]) == 64  # hex SHA256
            assert row["prev_hash"]  # non-empty (GENESIS or prior)

    def test_change_log_row_signatures_verify(self, db_session, org_a, monkeypatch, tmp_path):
        """Every row's signature must verify under the signer's pubkey.

        This is the core v2 guarantee — auditors can sample rows and
        verify them offline without trusting AI Identity's systems.
        """
        from common.compliance.change_log_signer import signing_input

        _seed_audit(db_session, org_a, monkeypatch)
        # Build with a known signer so we control the pubkey.
        signer, public_pem = _local_signer()
        bundle = ComplianceExportBundle.create(tmp_path / "soc2.zip", export_id=uuid.uuid4())
        now = datetime.datetime.now(tz=datetime.UTC)
        build_soc2_bundle(
            bundle,
            db=db_session,
            org_id=org_a["org"].id,
            export_id=bundle.export_id,
            audit_period_start=now - datetime.timedelta(days=30),
            audit_period_end=now + datetime.timedelta(days=1),
            built_at=now,
            agent_ids=None,
            signer=signer,
        )
        bundle.seal(
            profile="soc2_tsc_2017",
            audit_period_start=now - datetime.timedelta(days=30),
            audit_period_end=now + datetime.timedelta(days=1),
            built_at=now,
            org_id=org_a["org"].id,
            signer=signer,
        )

        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "change_log.csv")

        assert rows, "need at least one row to verify signatures"
        public_key = serialization.load_pem_public_key(public_pem)
        for row in rows:
            # Reconstruct the object-form diff/details for signing.
            diff_obj = json.loads(row["diff_json"]) if row["diff_json"] else {}
            details_obj = json.loads(row["details_json"]) if row["details_json"] else {}
            sig_row = dict(row)
            sig_row["audit_log_id"] = int(row["audit_log_id"])
            sig_row["diff_json"] = diff_obj
            sig_row["details_json"] = details_obj
            signing_bytes = signing_input(sig_row)
            sig_der = base64.b64decode(row["signature"])
            public_key.verify(sig_der, signing_bytes, ec.ECDSA(hashes.SHA256()))

    def test_change_log_schema_version_in_manifest(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["artifact_schema_versions"]["change_log.csv"] == "2.0"

    def test_verify_change_log_cli_exits_zero_on_valid_export(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        """End-to-end: build a real export, verify it with the CLI."""
        import subprocess
        import sys as _sys

        _seed_audit(db_session, org_a, monkeypatch)
        signer, public_pem = _local_signer()
        bundle = ComplianceExportBundle.create(tmp_path / "soc2.zip", export_id=uuid.uuid4())
        now = datetime.datetime.now(tz=datetime.UTC)
        build_soc2_bundle(
            bundle,
            db=db_session,
            org_id=org_a["org"].id,
            export_id=bundle.export_id,
            audit_period_start=now - datetime.timedelta(days=30),
            audit_period_end=now + datetime.timedelta(days=1),
            built_at=now,
            agent_ids=None,
            signer=signer,
        )
        bundle.seal(
            profile="soc2_tsc_2017",
            audit_period_start=now - datetime.timedelta(days=30),
            audit_period_end=now + datetime.timedelta(days=1),
            built_at=now,
            org_id=org_a["org"].id,
            signer=signer,
        )

        # Extract the CSV + write pubkey to disk for the CLI.
        csv_path = tmp_path / "change_log.csv"
        manifest_path = tmp_path / "manifest.json"
        pubkey_path = tmp_path / "pubkey.pem"
        pubkey_path.write_bytes(public_pem)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            csv_path.write_bytes(zf.read("change_log.csv"))
            manifest_path.write_bytes(zf.read("manifest.json"))

        repo_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [
                _sys.executable,
                str(repo_root / "scripts" / "verify_change_log.py"),
                "--pubkey",
                str(pubkey_path),
                "--manifest",
                str(manifest_path),
                str(csv_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"verify_change_log.py exited {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout


class TestAttestations:
    def test_attestation_envelope_round_trips(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        att = _seed_attestation(db_session, org_a)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            data = json.loads(zf.read(f"attestations/{att.session_id}.dsse.json"))
        assert data["payloadType"] == "application/vnd.ai-identity.attestation+json"
        assert data["signatures"][0]["keyid"] == "local:test"


class TestChainIntegrity:
    def test_chain_integrity_json_carries_verify_result(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            payload = json.loads(zf.read("chain_integrity.json"))
        assert payload["scope"] == "global"
        assert payload["valid"] is True
        assert payload["total_entries"] >= 4
        assert payload["entries_verified"] == payload["total_entries"]


class TestControlResults:
    def test_control_results_includes_every_report_row(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        _seed_control_results(db_session, org_a)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            rows = _read_csv(zf, "control_results.csv")
        assert len(rows) == 2
        statuses = {r["check_status"] for r in rows}
        assert statuses == {"pass", "warning"}


class TestPolicySnapshots:
    def test_policy_snapshot_contains_rules_and_version(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        _seed_policy(db_session, org_a)
        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            paths = [n for n in zf.namelist() if n.startswith("policy_snapshots/")]
            assert len(paths) == 1
            payload = json.loads(zf.read(paths[0]))
        assert payload["version"] == 2
        assert payload["is_active"] is True
        assert payload["rules"] == {"deny": [{"endpoint": "/admin/*"}]}


class TestEvidenceSummary:
    def test_summary_counts_match_artifact_contents(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        _seed_attestation(db_session, org_a)
        _seed_control_results(db_session, org_a)
        _seed_policy(db_session, org_a)

        bundle = _build_bundle(tmp_path, db_session, org_a)
        with zipfile.ZipFile(bundle.archive_path) as zf:
            summary = json.loads(zf.read("evidence_summary.json"))
            access_rows = _read_csv(zf, "access_log.csv")
            change_rows = _read_csv(zf, "change_log.csv")
            control_rows = _read_csv(zf, "control_results.csv")
            agent_rows = _read_csv(zf, "agent_inventory.csv")

        assert summary["profile"] == "soc2_tsc_2017"
        assert summary["counts"]["access_log"] == len(access_rows)
        assert summary["counts"]["change_log"] == len(change_rows)
        assert summary["counts"]["control_results"] == len(control_rows)
        assert summary["counts"]["agent_inventory"] == len(agent_rows)
        assert summary["counts"]["attestations"] == 1
        assert summary["counts"]["policy_snapshots"] == 1
        assert "SOC2-CC6.1" in summary["artifact_control_mapping"]["access_log.csv"]
        assert summary["chain_integrity"]["valid"] is True


class TestAgentScope:
    def test_agent_ids_filter_narrows_access_and_inventory(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        bundle = _build_bundle(
            tmp_path,
            db_session,
            org_a,
            agent_ids=[org_a["active"].id],  # narrow to the active agent only
        )
        with zipfile.ZipFile(bundle.archive_path) as zf:
            inventory = _read_csv(zf, "agent_inventory.csv")
            access = _read_csv(zf, "access_log.csv")
            change = _read_csv(zf, "change_log.csv")
        assert [r["agent_id"] for r in inventory] == [str(org_a["active"].id)]
        # Revoked-agent events disappear from the access + change logs.
        for row in access:
            assert row["agent_id"] == str(org_a["active"].id)
        for row in change:
            assert row["agent_id"] == str(org_a["active"].id)


class TestDeterminism:
    def test_same_inputs_produce_identical_artifact_bytes(
        self, db_session, org_a, monkeypatch, tmp_path
    ):
        _seed_audit(db_session, org_a, monkeypatch)
        _seed_attestation(db_session, org_a)
        _seed_control_results(db_session, org_a)
        _seed_policy(db_session, org_a)

        # Build twice, into distinct paths. Artifact bytes must match
        # for artifacts whose content is fully determined by DB state.
        # change_log.csv carries per-row ECDSA signatures (v2 schema)
        # and is non-deterministic for the same reason the outer
        # manifest envelope is — ECDSA nonce. Verified separately via
        # row-level signature verification in TestChangeLog.
        bundle_a = _build_bundle(tmp_path / "a", db_session, org_a)
        bundle_b = _build_bundle(tmp_path / "b", db_session, org_a)
        artifacts = [
            "agent_inventory.csv",
            "access_log.csv",
            "control_results.csv",
        ]
        with (
            zipfile.ZipFile(bundle_a.archive_path) as za,
            zipfile.ZipFile(bundle_b.archive_path) as zb,
        ):
            for name in artifacts:
                assert za.read(name) == zb.read(name), f"{name} diverged"


class TestManifestCommits:
    def test_manifest_covers_every_written_artifact(self, db_session, org_a, monkeypatch, tmp_path):
        _seed_audit(db_session, org_a, monkeypatch)
        _seed_attestation(db_session, org_a)
        _seed_control_results(db_session, org_a)
        _seed_policy(db_session, org_a)

        bundle = _build_bundle(tmp_path, db_session, org_a)
        env = bundle.manifest_envelope
        manifest = json.loads(base64.b64decode(env.payload))
        manifest_paths = {a["path"] for a in manifest["artifacts"]}

        with zipfile.ZipFile(bundle.archive_path) as zf:
            archive_paths = set(zf.namelist()) - {"manifest.json", "manifest.dsse.json"}
        # Every artifact is in the manifest.
        assert archive_paths == manifest_paths
        # Every manifest entry has a 64-hex hash + non-negative byte count.
        for entry in manifest["artifacts"]:
            assert len(entry["sha256"]) == 64
            assert entry["bytes"] >= 0
