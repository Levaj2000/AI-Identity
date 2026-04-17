"""Tests for the compliance export API stub (#273).

The endpoints return 501 on happy-path calls — they're a contract
today, a live implementation later. These tests pin:

1. The 501 error envelope shape (so clients can handle it uniformly).
2. That real validation runs *before* the 501 — a bad request fails
   fast with 400, not 501, so client integration tests have real
   failure cases to work with.
3. That authZ runs before the 501 — non-admins get 403.
4. That cross-tenant protections run before the 501.
5. That OpenAPI surfaces the endpoints with the correct tag.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from common.audit import create_audit_entry  # noqa: F401 — kept for future integration tests
from common.models import Agent, Organization, OrgMembership, User

ORG_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ORG_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER_A_EMAIL = "owner-a@example.test"
OWNER_B_EMAIL = "owner-b@example.test"
MEMBER_A_EMAIL = "member-a@example.test"


@pytest.fixture
def two_orgs(db_session):
    """One agent per org + an owner and a plain member in org A."""
    owner_a = User(id=uuid.uuid4(), email=OWNER_A_EMAIL, role="owner", tier="enterprise")
    owner_b = User(id=uuid.uuid4(), email=OWNER_B_EMAIL, role="owner", tier="enterprise")
    member_a = User(id=uuid.uuid4(), email=MEMBER_A_EMAIL, role="owner", tier="enterprise")
    db_session.add_all([owner_a, owner_b, member_a])
    db_session.flush()

    org_a = Organization(id=ORG_A_ID, name="Org A", owner_id=owner_a.id, tier="business")
    org_b = Organization(id=ORG_B_ID, name="Org B", owner_id=owner_b.id, tier="business")
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


# ── Stub 501 shape ───────────────────────────────────────────────────


class TestStubShape:
    def test_post_valid_body_returns_501_with_stable_code(self, client, two_orgs):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 501, resp.text
        body = resp.json()
        assert body["error"]["code"] == "export_builder_not_implemented"
        # Stub echoes the validated profile + resolved org_id so a
        # client's integration test can confirm its payload reached
        # the handler before the 501.
        assert body["error"]["profile"] == "soc2_tsc_2017"
        assert body["error"]["org_id"] == str(ORG_A_ID)

    def test_get_by_id_returns_501(self, client, two_orgs):
        resp = client.get(
            f"/api/v1/exports/{uuid.uuid4()}",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 501
        assert resp.json()["error"]["code"] == "export_builder_not_implemented"

    def test_list_returns_501(self, client, two_orgs):
        resp = client.get(
            "/api/v1/exports",
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 501


# ── Validation happens before 501 ────────────────────────────────────


class TestValidationBeforeStub:
    def test_bad_profile_enum_is_400(self, client, two_orgs):
        body = _valid_body(profile="not_a_real_framework")
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        # Pydantic validation → 422 from FastAPI
        assert resp.status_code in (400, 422)

    def test_reversed_period_is_400(self, client, two_orgs):
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

    def test_period_over_max_is_rejected(self, client, two_orgs):
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


# ── AuthZ before 501 ────────────────────────────────────────────────


class TestAuthzBeforeStub:
    def test_plain_member_gets_403(self, client, two_orgs):
        resp = client.post(
            "/api/v1/exports",
            json=_valid_body(),
            headers={"X-API-Key": MEMBER_A_EMAIL},
        )
        assert resp.status_code == 403


# ── Cross-tenant protection before 501 ──────────────────────────────


class TestCrossOrgProtection:
    def test_agent_id_from_other_org_rejected_400(self, client, two_orgs):
        # Owner A tries to export with Agent B's id mixed in
        body = _valid_body(agent_ids=[str(two_orgs["agent_a"].id), str(two_orgs["agent_b"].id)])
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 400
        assert "different org" in resp.json()["error"]["message"]

    def test_unknown_agent_id_rejected_400(self, client, two_orgs):
        body = _valid_body(agent_ids=[str(uuid.uuid4())])
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 400
        assert "not found" in resp.json()["error"]["message"]

    def test_own_agent_ids_pass_through_to_501(self, client, two_orgs):
        """Valid own-org agent_ids should reach the stub — proving the
        cross-tenant check doesn't over-reject.
        """
        body = _valid_body(agent_ids=[str(two_orgs["agent_a"].id)])
        resp = client.post(
            "/api/v1/exports",
            json=body,
            headers={"X-API-Key": OWNER_A_EMAIL},
        )
        assert resp.status_code == 501


# ── OpenAPI surfaces the endpoints ───────────────────────────────────


class TestOpenAPI:
    def test_routes_present_with_correct_tag(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths", {})
        assert "/api/v1/exports" in paths
        assert "/api/v1/exports/{export_id}" in paths

        post = paths["/api/v1/exports"]["post"]
        assert "compliance.exports" in post["tags"]
        # 501 response is documented so generated clients know about it
        assert "501" in post["responses"]

    def test_profile_enum_in_schema(self, client):
        spec = client.get("/openapi.json").json()
        schemas = spec.get("components", {}).get("schemas", {})
        assert "ExportProfile" in schemas
        enum_values = schemas["ExportProfile"].get("enum", [])
        assert "soc2_tsc_2017" in enum_values
        assert "eu_ai_act_2024" in enum_values
        assert "nist_ai_rmf_1_0" in enum_values
