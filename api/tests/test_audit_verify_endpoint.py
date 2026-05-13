"""Tests for the org-scoped /api/v1/audit/verify endpoint (Phase 3).

Closes the cross-tenant info-leak that motivated the per-org chain
migration: a tenant calling /verify should see only their own chain.
"""

import uuid

from common.audit import create_audit_entry
from common.models import Agent, Organization, OrgMembership, User

ORG_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ORG_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER_A_EMAIL = "verify-owner-a@test"
OWNER_B_EMAIL = "verify-owner-b@test"


def _seed_two_orgs_with_entries(db):
    """Create org A (3 entries) and org B (2 entries). Return owners + agents."""
    owner_a = User(id=uuid.uuid4(), email=OWNER_A_EMAIL, role="owner", tier="enterprise")
    owner_b = User(id=uuid.uuid4(), email=OWNER_B_EMAIL, role="owner", tier="enterprise")
    db.add_all([owner_a, owner_b])
    db.flush()

    org_a = Organization(id=ORG_A_ID, name="Org A", owner_id=owner_a.id, tier="business")
    org_b = Organization(id=ORG_B_ID, name="Org B", owner_id=owner_b.id, tier="business")
    db.add_all([org_a, org_b])
    db.flush()

    owner_a.org_id = ORG_A_ID
    owner_b.org_id = ORG_B_ID
    db.add_all(
        [
            OrgMembership(org_id=ORG_A_ID, user_id=owner_a.id, role="owner"),
            OrgMembership(org_id=ORG_B_ID, user_id=owner_b.id, role="owner"),
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
    db.add_all([agent_a, agent_b])
    db.commit()

    for _ in range(3):
        create_audit_entry(
            db,
            agent_id=agent_a.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
    for _ in range(2):
        create_audit_entry(
            db,
            agent_id=agent_b.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
    return owner_a, owner_b, agent_a, agent_b


class TestVerifyEndpointOrgIsolation:
    def test_default_scopes_to_callers_org(self, client, db_session):
        """No org_id query param: response covers only the caller's org."""
        _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": OWNER_A_EMAIL}

        resp = client.get("/api/v1/audit/verify", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        # Org A wrote 3 entries — caller sees those, not the 5 total
        assert body["total_entries"] == 3
        assert body["entries_verified"] == 3
        assert body["valid"] is True

    def test_foreign_org_id_blocked_for_non_admin(self, client, db_session):
        """Owner of A passing ?org_id=<B's id> gets 403, not data."""
        _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": OWNER_A_EMAIL}

        resp = client.get(f"/api/v1/audit/verify?org_id={ORG_B_ID}", headers=headers)

        assert resp.status_code == 403

    def test_own_org_id_explicit_works(self, client, db_session):
        """Caller passing their own org_id is fine (same as default)."""
        _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": OWNER_A_EMAIL}

        resp = client.get(f"/api/v1/audit/verify?org_id={ORG_A_ID}", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["total_entries"] == 3

    def test_no_org_context_returns_400(self, client, db_session):
        """User with no org_id and no ?org_id param: bad request."""
        # Seed a user with no org_id
        u = User(id=uuid.uuid4(), email="no-org@test", role="owner", tier="enterprise")
        db_session.add(u)
        db_session.commit()
        headers = {"X-API-Key": "no-org@test"}

        resp = client.get("/api/v1/audit/verify", headers=headers)

        assert resp.status_code == 400

    def test_agent_id_from_other_org_returns_404(self, client, db_session):
        """Probing for a foreign org's agent via agent_id returns 404."""
        _, _, _, agent_b = _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": OWNER_A_EMAIL}

        resp = client.get(f"/api/v1/audit/verify?agent_id={agent_b.id}", headers=headers)

        assert resp.status_code == 404


class TestVerifyEndpointPlatformAdmin:
    def test_admin_can_pass_foreign_org_id(self, client, db_session, admin_user):
        """Platform admin verifies any org's chain."""
        _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": admin_user.email}

        resp = client.get(f"/api/v1/audit/verify?org_id={ORG_B_ID}", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_entries"] == 2
        assert body["valid"] is True


class TestVerifyGlobalEndpoint:
    def test_non_admin_gets_403(self, client, db_session):
        """Non-admin cannot access the platform-wide chain endpoint."""
        _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": OWNER_A_EMAIL}

        resp = client.get("/api/v1/audit/verify/global", headers=headers)

        assert resp.status_code == 403

    def test_admin_can_verify_global_chain(self, client, db_session, admin_user):
        """Platform admin sees the full platform-wide chain (5 entries)."""
        _seed_two_orgs_with_entries(db_session)
        headers = {"X-API-Key": admin_user.email}

        resp = client.get("/api/v1/audit/verify/global", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_entries"] == 5
        assert body["entries_verified"] == 5
        assert body["valid"] is True
