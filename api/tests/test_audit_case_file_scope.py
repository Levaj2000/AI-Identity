"""Tests for Case File export scope extension (#403).

GET /api/v1/audit/report (and /report/bundle) scope by one of:
  - agent_id      → single agent (legacy default; ownership enforced)
  - correlation_id → one incident (events sharing the id, org-admin only)
  - neither        → org-wide (every agent in the tenant, org-admin only)

Covers backward compatibility (agent scope unchanged), the new org-wide and
incident scopes, cross-org isolation, and the org-admin authorization gate.
"""

import uuid

from common.audit import create_audit_entry
from common.models import Agent, Organization, OrgMembership, User

ORG_A_ID = uuid.UUID("a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1")
ORG_B_ID = uuid.UUID("b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1")
OWNER_A = "cf-owner-a@test"
OWNER_B = "cf-owner-b@test"
MEMBER_A = "cf-member-a@test"

WINDOW = "start_date=2020-01-01T00:00:00&end_date=2030-01-01T00:00:00"


def _seed(db_session):
    """Two orgs; owner + plain member in A, owner in B; one agent per org."""
    owner_a = User(id=uuid.uuid4(), email=OWNER_A, role="owner", tier="enterprise")
    owner_b = User(id=uuid.uuid4(), email=OWNER_B, role="owner", tier="enterprise")
    member_a = User(id=uuid.uuid4(), email=MEMBER_A, role="owner", tier="enterprise")
    db_session.add_all([owner_a, owner_b, member_a])
    db_session.flush()

    org_a = Organization(
        id=ORG_A_ID,
        name="CF Org A",
        owner_id=owner_a.id,
        tier="business",
        forensic_verify_key="cf-org-a-forensic-key-0123456789abcdef",
    )
    org_b = Organization(id=ORG_B_ID, name="CF Org B", owner_id=owner_b.id, tier="business")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    owner_a.org_id = ORG_A_ID
    owner_b.org_id = ORG_B_ID
    member_a.org_id = ORG_A_ID
    db_session.add_all(
        [
            OrgMembership(org_id=ORG_A_ID, user_id=owner_a.id, role="owner"),
            OrgMembership(org_id=ORG_B_ID, user_id=owner_b.id, role="owner"),
            OrgMembership(org_id=ORG_A_ID, user_id=member_a.id, role="member"),
        ]
    )

    agent_a = Agent(
        id=uuid.uuid4(),
        user_id=owner_a.id,
        org_id=ORG_A_ID,
        name="CF Agent A",
        status="active",
        capabilities=[],
        metadata_={},
    )
    # A second agent in org A owned by the member — exercises org-wide reach.
    agent_a2 = Agent(
        id=uuid.uuid4(),
        user_id=member_a.id,
        org_id=ORG_A_ID,
        name="CF Agent A2",
        status="active",
        capabilities=[],
        metadata_={},
    )
    agent_b = Agent(
        id=uuid.uuid4(),
        user_id=owner_b.id,
        org_id=ORG_B_ID,
        name="CF Agent B",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add_all([agent_a, agent_a2, agent_b])
    db_session.commit()
    return agent_a, agent_a2, agent_b


def _entry(db_session, agent_id, endpoint, correlation_id=None):
    return create_audit_entry(
        db_session,
        agent_id=agent_id,
        endpoint=endpoint,
        method="POST",
        decision="allow",
        request_metadata={},
        correlation_id=correlation_id,
    )


# ── Report signature must verify with the ORG key (not the server key) ───


class TestReportSignatureUsesOrgKey:
    def test_report_signature_verifies_with_org_forensic_key(self, client, db_session):
        """The report signature must recompute with the org's forensic key — the
        same key that ships in the bundle and verifies the chain — so a key-holder
        can verify it offline (the Reliability Statement's promise)."""
        from datetime import datetime

        from common.audit import generate_report_signature

        agent_a, _, _ = _seed(db_session)
        _entry(db_session, agent_a.id, "/v1/a")
        resp = client.get(
            f"/api/v1/audit/report?agent_id={agent_a.id}&{WINDOW}&format=json",
            headers={"X-API-Key": OWNER_A},
        )
        assert resp.status_code == 200
        body = resp.json()
        cv = body["chain_verification"]
        expected = generate_report_signature(
            report_id=body["report_id"],
            generated_at=datetime.fromisoformat(body["generated_at"]),
            chain_valid=cv["valid"],
            total_entries=cv["total_entries"],
            entries_verified=cv["entries_verified"],
            hmac_key="cf-org-a-forensic-key-0123456789abcdef",
        )
        assert expected == body["report_signature"]


# ── Backward compatibility: agent scope unchanged ────────────────────


class TestAgentScopeStillWorks:
    def test_agent_scoped_report_is_unchanged(self, client, db_session):
        agent_a, _, _ = _seed(db_session)
        _entry(db_session, agent_a.id, "/v1/a")
        headers = {"X-API-Key": OWNER_A}

        resp = client.get(
            f"/api/v1/audit/report?agent_id={agent_a.id}&{WINDOW}&format=json",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent"]["id"] == str(agent_a.id)
        assert body["scope"]["type"] == "agent"
        assert len(body["events"]) == 1


# ── Org-wide scope ───────────────────────────────────────────────────


class TestOrgWideScope:
    def test_org_owner_gets_all_org_agents(self, client, db_session):
        agent_a, agent_a2, agent_b = _seed(db_session)
        _entry(db_session, agent_a.id, "/v1/a")
        _entry(db_session, agent_a2.id, "/v1/a2")  # owned by member, same org
        _entry(db_session, agent_b.id, "/v1/b")  # different org — must be excluded
        headers = {"X-API-Key": OWNER_A}

        resp = client.get(f"/api/v1/audit/report?{WINDOW}&format=json", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent"] is None
        assert body["scope"]["type"] == "org"
        assert body["scope"]["org_id"] == str(ORG_A_ID)
        endpoints = {e["endpoint"] for e in body["events"]}
        assert endpoints == {"/v1/a", "/v1/a2"}  # no org B leakage

    def test_member_cannot_export_org_wide(self, client, db_session):
        _seed(db_session)
        headers = {"X-API-Key": MEMBER_A}  # membership role = member, not admin
        resp = client.get(f"/api/v1/audit/report?{WINDOW}&format=json", headers=headers)
        assert resp.status_code == 403

    def test_owner_cannot_export_foreign_org(self, client, db_session):
        _seed(db_session)
        headers = {"X-API-Key": OWNER_A}
        resp = client.get(
            f"/api/v1/audit/report?org_id={ORG_B_ID}&{WINDOW}&format=json",
            headers=headers,
        )
        assert resp.status_code == 403


# ── Incident (correlation_id) scope ──────────────────────────────────


class TestIncidentScope:
    def test_correlation_scoped_report(self, client, db_session):
        agent_a, agent_a2, _ = _seed(db_session)
        corr = "incident-42"
        _entry(db_session, agent_a.id, "/v1/in", correlation_id=corr)
        _entry(db_session, agent_a2.id, "/v1/in2", correlation_id=corr)
        _entry(db_session, agent_a.id, "/v1/other", correlation_id="unrelated")
        headers = {"X-API-Key": OWNER_A}

        resp = client.get(
            f"/api/v1/audit/report?correlation_id={corr}&format=json", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["scope"]["type"] == "incident"
        assert body["scope"]["correlation_id"] == corr
        endpoints = {e["endpoint"] for e in body["events"]}
        assert endpoints == {"/v1/in", "/v1/in2"}

    def test_member_cannot_export_incident(self, client, db_session):
        _seed(db_session)
        headers = {"X-API-Key": MEMBER_A}
        resp = client.get(
            "/api/v1/audit/report?correlation_id=incident-42&format=json", headers=headers
        )
        assert resp.status_code == 403


# ── Bundle inherits the same scoping ─────────────────────────────────


class TestBundleScope:
    def test_org_wide_bundle_downloads(self, client, db_session):
        agent_a, _, _ = _seed(db_session)
        _entry(db_session, agent_a.id, "/v1/a")
        headers = {"X-API-Key": OWNER_A}

        resp = client.get(f"/api/v1/audit/report/bundle?{WINDOW}", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "ai-identity-case-file-" in resp.headers["content-disposition"]

    def test_bundle_is_self_contained_includes_verifier(self, client, db_session):
        """The bundle MUST contain the verifier script + report + README — a
        customer should never have to source the verifier separately."""
        import io
        import zipfile

        agent_a, _, _ = _seed(db_session)
        _entry(db_session, agent_a.id, "/v1/a")
        resp = client.get(
            f"/api/v1/audit/report/bundle?agent_id={agent_a.id}&{WINDOW}",
            headers={"X-API-Key": OWNER_A},
        )
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert "ai_identity_verify.py" in names, f"verifier missing from bundle: {names}"
        assert len(zf.read("ai_identity_verify.py")) > 1000  # a real script, not a stub
        assert "README.md" in names
        assert any(n.startswith("case-file-") and n.endswith(".json") for n in names)
