"""Tests for audit_log.org_id + org-scoped admin endpoint.

Covers:
  - Writer populates org_id from agent.org_id
  - Writer falls back to the sentinel system org for shadow / orphan entries
  - HMAC integrity chain still verifies after org_id was added (since org_id
    is NOT part of the canonical payload)
  - GET /api/v1/audit/admin requires org owner/admin role
  - Cross-org isolation: owner of org A cannot see org B's entries
  - Org owner gets org-wide visibility on the user-facing /audit endpoint
"""

import uuid

from common.audit import create_audit_entry, verify_chain
from common.models import Agent, Organization, OrgMembership, User
from common.models.organization import SYSTEM_ORG_ID

# ── Fixtures ─────────────────────────────────────────────────────────


ORG_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ORG_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_OWNER_EMAIL = "owner-org-a@test"
USER_B_OWNER_EMAIL = "owner-org-b@test"
USER_A_MEMBER_EMAIL = "member-org-a@test"


def _seed_two_orgs(db_session):
    """Create two orgs with one owner each and one plain member in org A.

    Returns (org_a, org_b, owner_a, owner_b, member_a, agent_a, agent_b).
    """
    owner_a = User(id=uuid.uuid4(), email=USER_A_OWNER_EMAIL, role="owner", tier="enterprise")
    owner_b = User(id=uuid.uuid4(), email=USER_B_OWNER_EMAIL, role="owner", tier="enterprise")
    member_a = User(id=uuid.uuid4(), email=USER_A_MEMBER_EMAIL, role="owner", tier="enterprise")
    db_session.add_all([owner_a, owner_b, member_a])
    db_session.flush()

    org_a = Organization(id=ORG_A_ID, name="Org A", owner_id=owner_a.id, tier="business")
    org_b = Organization(id=ORG_B_ID, name="Org B", owner_id=owner_b.id, tier="business")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    # Wire up memberships + user.org_id
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

    # One agent per org
    agent_a = Agent(
        id=uuid.uuid4(),
        user_id=owner_a.id,
        org_id=ORG_A_ID,
        name="Agent A",
        status="active",
        capabilities=[],
        metadata_={},
    )
    agent_b = Agent(
        id=uuid.uuid4(),
        user_id=owner_b.id,
        org_id=ORG_B_ID,
        name="Agent B",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add_all([agent_a, agent_b])
    db_session.commit()
    return org_a, org_b, owner_a, owner_b, member_a, agent_a, agent_b


# ── Writer ───────────────────────────────────────────────────────────


class TestWriterPopulatesOrgId:
    def test_entry_inherits_org_from_agent(self, db_session):
        _, _, owner_a, _, _, agent_a, _ = _seed_two_orgs(db_session)

        entry = create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={"model": "gpt-4"},
        )

        assert entry.org_id == ORG_A_ID
        assert entry.user_id == owner_a.id

    def test_shadow_entry_routes_to_system_org(self, db_session):
        """Entry for an unregistered agent_id lands in the sentinel system org."""
        unknown_agent_id = uuid.uuid4()

        entry = create_audit_entry(
            db_session,
            agent_id=unknown_agent_id,
            endpoint="/v1/chat",
            method="POST",
            decision="deny",
            request_metadata={"deny_reason": "agent_not_found"},
        )

        assert entry.org_id == SYSTEM_ORG_ID
        # System org was auto-created
        sys_org = db_session.query(Organization).filter(Organization.id == SYSTEM_ORG_ID).first()
        assert sys_org is not None

    def test_hmac_chain_intact_with_org_id(self, db_session):
        """org_id is access-control metadata, NOT in the hash. Chain must verify."""
        _, _, _, _, _, agent_a, agent_b = _seed_two_orgs(db_session)

        for agent in (agent_a, agent_b, agent_a):
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint="/v1/chat",
                method="POST",
                decision="allow",
                request_metadata={},
            )

        result = verify_chain(db_session)
        assert result.valid is True
        assert result.entries_verified == 3


# ── /admin endpoint: access control ──────────────────────────────────


class TestAdminEndpointAccessControl:
    def test_member_cannot_read_org_admin_view(self, client, db_session, auth_headers):
        """A plain member (role=member) gets 403 on /audit/admin."""
        _seed_two_orgs(db_session)
        headers = {"X-API-Key": USER_A_MEMBER_EMAIL}

        resp = client.get(f"/api/v1/audit/admin?org_id={ORG_A_ID}", headers=headers)
        assert resp.status_code == 403

    def test_owner_of_wrong_org_gets_403(self, client, db_session):
        """Owner of Org A cannot view Org B's audit entries."""
        _seed_two_orgs(db_session)
        headers = {"X-API-Key": USER_A_OWNER_EMAIL}

        resp = client.get(f"/api/v1/audit/admin?org_id={ORG_B_ID}", headers=headers)
        assert resp.status_code == 403

    def test_owner_sees_only_their_org(self, client, db_session):
        """Owner of Org A gets Org A's entries scoped strictly."""
        _, _, _, _, _, agent_a, agent_b = _seed_two_orgs(db_session)

        # Write one entry in each org
        create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        create_audit_entry(
            db_session,
            agent_id=agent_b.id,
            endpoint="/v1/b",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        headers = {"X-API-Key": USER_A_OWNER_EMAIL}
        resp = client.get(f"/api/v1/audit/admin?org_id={ORG_A_ID}", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["endpoint"] == "/v1/a"
        assert body["items"][0]["org_id"] == str(ORG_A_ID)

    def test_missing_org_id_returns_422(self, client, db_session):
        """org_id is required — /admin without it is a validation error."""
        _seed_two_orgs(db_session)
        headers = {"X-API-Key": USER_A_OWNER_EMAIL}

        resp = client.get("/api/v1/audit/admin", headers=headers)
        assert resp.status_code == 422


# ── /audit user endpoint: org-admin sees all agents in org ───────────


class TestUserListOrgAdminVisibility:
    def test_org_owner_sees_other_members_agents(self, client, db_session):
        """Owner of Org A sees entries for agents owned by other members in Org A."""
        _, _, owner_a, _, member_a, _, _ = _seed_two_orgs(db_session)

        # Create an agent owned by member_a (not by owner_a) in Org A
        member_agent = Agent(
            id=uuid.uuid4(),
            user_id=member_a.id,
            org_id=ORG_A_ID,
            name="Member Agent",
            status="active",
            capabilities=[],
            metadata_={},
        )
        db_session.add(member_agent)
        db_session.commit()

        create_audit_entry(
            db_session,
            agent_id=member_agent.id,
            endpoint="/v1/by-member",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        headers = {"X-API-Key": USER_A_OWNER_EMAIL}
        resp = client.get("/api/v1/audit", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        endpoints = [item["endpoint"] for item in body["items"]]
        assert "/v1/by-member" in endpoints

    def test_org_owner_does_not_see_other_org_entries(self, client, db_session):
        """Owner of Org A never sees Org B's entries on the user-facing /audit."""
        _, _, _, _, _, agent_a, agent_b = _seed_two_orgs(db_session)

        create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        create_audit_entry(
            db_session,
            agent_id=agent_b.id,
            endpoint="/v1/b",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        headers = {"X-API-Key": USER_A_OWNER_EMAIL}
        resp = client.get("/api/v1/audit", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        endpoints = [item["endpoint"] for item in body["items"]]
        assert "/v1/a" in endpoints
        assert "/v1/b" not in endpoints
