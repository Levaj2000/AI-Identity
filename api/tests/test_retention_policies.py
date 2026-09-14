"""Tests for the forensic retention policy API (v0.5.0, phase 2).

Covers policy CRUD with create-time validation, the explain endpoint,
legal holds, and the retention-event feed.
"""

import uuid
from datetime import UTC, datetime, timedelta

from common.models import Organization, OrgMembership, User

ENTERPRISE_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_user_org(db_session, tier, tag):
    """Create a user + org of the given tier with an owner membership."""
    user = User(
        id=uuid.uuid4(),
        email=f"retention-{tag}-{uuid.uuid4().hex[:8]}@test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(user)
    db_session.flush()
    org = Organization(id=uuid.uuid4(), name=f"Retention {tier} {tag}", owner_id=user.id, tier=tier)
    db_session.add(org)
    db_session.flush()
    user.org_id = org.id
    db_session.add(OrgMembership(org_id=org.id, user_id=user.id, role="owner"))
    db_session.commit()
    return user, org


def _auth(user):
    return {"X-API-Key": user.email}


def _policy_body(**overrides):
    body = {
        "rules": [
            {"rule_id": "r_deny", "selector": {"decision": ["deny"]}, "retain_for": "P90D"},
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ],
        "default_rule": {"retain_for": "P90D"},
    }
    body.update(overrides)
    return body


def _url(org_id):
    return f"/api/v1/organizations/{org_id}/retention"


# ── Policy CRUD + validation ─────────────────────────────────────────────


def test_create_policy_happy_path(client, db_session, test_user):
    resp = client.post(
        f"{_url(ENTERPRISE_ORG_ID)}/policies",
        json=_policy_body(),
        headers=_auth(test_user),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["version"] == 1
    assert data["status"] == "active"
    assert data["policy_id"].startswith("retpol_")
    assert data["warnings"] == []
    assert data["created_by"] == str(test_user.id)  # opaque principal, not email

    # Versions list + active endpoints agree.
    versions = client.get(f"{_url(ENTERPRISE_ORG_ID)}/policies", headers=_auth(test_user)).json()
    assert [v["version"] for v in versions] == [1]
    active = client.get(
        f"{_url(ENTERPRISE_ORG_ID)}/policies/active", headers=_auth(test_user)
    ).json()
    assert active["id"] == data["id"]


def test_create_policy_missing_catch_all(client, db_session, test_user):
    body = _policy_body(
        rules=[{"rule_id": "r1", "selector": {"decision": ["deny"]}, "retain_for": "P90D"}]
    )
    resp = client.post(f"{_url(ENTERPRISE_ORG_ID)}/policies", json=body, headers=_auth(test_user))
    assert resp.status_code == 400, resp.text
    assert "catch-all" in resp.text


def test_create_policy_shadowed_rule_rejected(client, db_session, test_user):
    body = _policy_body(
        rules=[
            {
                "rule_id": "r_broad",
                "selector": {"decision": ["deny", "allow"]},
                "retain_for": "P60D",
            },
            {"rule_id": "r_narrow", "selector": {"decision": ["deny"]}, "retain_for": "P60D"},
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P60D"},
        ]
    )
    resp = client.post(f"{_url(ENTERPRISE_ORG_ID)}/policies", json=body, headers=_auth(test_user))
    assert resp.status_code == 400, resp.text
    assert "shadowed" in resp.text
    assert "r_narrow" in resp.text


def test_create_policy_broad_before_narrow_warns(client, db_session, test_user):
    body = _policy_body(
        rules=[
            {"rule_id": "r1", "selector": {"decision": ["deny"]}, "retain_for": "P60D"},
            {"rule_id": "r2", "selector": {"flow_tag": ["prod"]}, "retain_for": "P60D"},
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P60D"},
        ]
    )
    resp = client.post(f"{_url(ENTERPRISE_ORG_ID)}/policies", json=body, headers=_auth(test_user))
    assert resp.status_code == 201, resp.text
    warnings = resp.json()["warnings"]
    assert warnings, "expected a broad-before-narrow warning"
    assert any("r1" in w and "r2" in w for w in warnings)


def test_create_policy_free_tier_forbidden(client, db_session):
    user, org = _make_user_org(db_session, "free", "free")
    resp = client.post(f"{_url(org.id)}/policies", json=_policy_body(), headers=_auth(user))
    assert resp.status_code == 403, resp.text


def test_create_policy_pro_ceiling_violation(client, db_session):
    user, org = _make_user_org(db_session, "pro", "pro")
    body = _policy_body(
        rules=[
            {"rule_id": "r1", "selector": {"decision": ["deny"]}, "retain_for": "P91D"},
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ]
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 400, resp.text
    assert "ceiling" in resp.text

    # Exactly at the ceiling is fine.
    body["rules"][0]["retain_for"] = "P90D"
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 201, resp.text


def test_create_policy_enterprise_indefinite_allowed(client, db_session):
    user, org = _make_user_org(db_session, "enterprise", "ent")
    body = _policy_body(
        rules=[
            {
                "rule_id": "r1",
                "selector": {"decision": ["deny"]},
                "retain_for": "indefinite",
            },
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "indefinite"},
        ],
        default_rule={"retain_for": "indefinite"},
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 201, resp.text


def test_create_policy_platform_floor(client, db_session):
    user, org = _make_user_org(db_session, "business", "floor")
    body = _policy_body(
        rules=[
            {"rule_id": "r1", "selector": {"decision": ["deny"]}, "retain_for": "P29D"},
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ]
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 400, resp.text
    assert "floor" in resp.text


def test_create_policy_regulated_minimum(client, db_session):
    user, org = _make_user_org(db_session, "business", "reg")
    body = _policy_body(
        rules=[
            {
                "rule_id": "r1",
                "selector": {"flow_tag": ["regulated"]},
                "retain_for": "P90D",
            },
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ]
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 400, resp.text
    assert "regulated" in resp.text


def test_create_policy_rejects_months_duration(client, db_session):
    user, org = _make_user_org(db_session, "business", "months")
    body = _policy_body(
        rules=[
            {"rule_id": "r1", "selector": {"decision": ["deny"]}, "retain_for": "P6M"},
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ]
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 400, resp.text
    assert "P1M" in resp.text or "months" in resp.text


def test_create_policy_redact_after_must_be_less(client, db_session):
    user, org = _make_user_org(db_session, "business", "redact")
    body = _policy_body(
        rules=[
            {
                "rule_id": "r1",
                "selector": {"decision": ["deny"]},
                "retain_for": "P90D",
                "redact_after": "P90D",
            },
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ]
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 400, resp.text
    assert "redact_after" in resp.text


def test_create_policy_bad_sampling_alg(client, db_session):
    user, org = _make_user_org(db_session, "business", "sampling")
    body = _policy_body(
        rules=[
            {
                "rule_id": "r1",
                "selector": {"decision": ["deny"]},
                "retain_for": "P90D",
                "sampling": {"alg": "md5-mod-v1", "of": 100, "keep": 10},
            },
            {"rule_id": "r_catchall", "selector": {}, "retain_for": "P90D"},
        ]
    )
    resp = client.post(f"{_url(org.id)}/policies", json=body, headers=_auth(user))
    assert resp.status_code == 400, resp.text
    assert "sha256-mod-v1" in resp.text


# ── Shortening friction ──────────────────────────────────────────────────


def test_shortening_requires_dual_approval(client, db_session):
    user, org = _make_user_org(db_session, "business", "shorten")
    headers = _auth(user)
    url = f"{_url(org.id)}/policies"

    v1 = client.post(url, json=_policy_body(), headers=headers)
    assert v1.status_code == 201, v1.text

    shortened = _policy_body()
    shortened["rules"][0]["retain_for"] = "P60D"  # was P90D

    # No approvals -> 400.
    resp = client.post(url, json=shortened, headers=headers)
    assert resp.status_code == 400, resp.text
    assert "dual approval" in resp.text

    # One approver -> still 400.
    now = datetime.now(UTC).isoformat()
    shortened["approvals"] = [{"by": "principal_a", "at": now}]
    resp = client.post(url, json=shortened, headers=headers)
    assert resp.status_code == 400, resp.text

    # Two distinct approvers, no effective_at -> 201 with delayed effect default.
    shortened["approvals"] = [
        {"by": "principal_a", "at": now},
        {"by": "principal_b", "at": now},
    ]
    resp = client.post(url, json=shortened, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["version"] == 2
    effective = datetime.fromisoformat(data["effective_at"])
    created = datetime.fromisoformat(data["created_at"])
    assert effective - created >= timedelta(days=6, hours=23)

    # Old version flipped to superseded; active is v2.
    versions = client.get(url, headers=headers).json()
    assert [(v["version"], v["status"]) for v in versions] == [
        (2, "active"),
        (1, "superseded"),
    ]
    active = client.get(f"{url}/active", headers=headers).json()
    assert active["version"] == 2
    assert active["policy_id"] == v1.json()["policy_id"]  # stable across versions


def test_shortening_rejects_early_effective_at(client, db_session):
    user, org = _make_user_org(db_session, "business", "early")
    headers = _auth(user)
    url = f"{_url(org.id)}/policies"
    assert client.post(url, json=_policy_body(), headers=headers).status_code == 201

    now = datetime.now(UTC)
    shortened = _policy_body()
    shortened["rules"][0]["retain_for"] = "P60D"
    shortened["approvals"] = [
        {"by": "principal_a", "at": now.isoformat()},
        {"by": "principal_b", "at": now.isoformat()},
    ]
    shortened["effective_at"] = (now + timedelta(days=1)).isoformat()
    resp = client.post(url, json=shortened, headers=headers)
    assert resp.status_code == 400, resp.text
    assert "7 days" in resp.text


# ── Explain ──────────────────────────────────────────────────────────────


def test_explain_returns_first_match(client, db_session, test_user):
    headers = _auth(test_user)
    url = f"{_url(ENTERPRISE_ORG_ID)}/policies"
    assert client.post(url, json=_policy_body(), headers=headers).status_code == 201

    resp = client.post(f"{url}/explain", json={"decision": "deny"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rule_id"] == "r_deny"
    assert resp.json()["matched_index"] == 0

    # No key carried -> falls through to the catch-all.
    resp = client.post(f"{url}/explain", json={"decision": "allow"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rule_id"] == "r_catchall"
    assert resp.json()["matched_index"] == 1


def test_explain_no_active_policy_404(client, db_session):
    user, org = _make_user_org(db_session, "business", "noexplain")
    resp = client.post(
        f"{_url(org.id)}/policies/explain",
        json={"decision": "deny"},
        headers=_auth(user),
    )
    assert resp.status_code == 404, resp.text


# ── Legal holds ─────────────────────────────────────────────────────────


def test_hold_place_and_release(client, db_session):
    user, org = _make_user_org(db_session, "business", "holds")
    headers = _auth(user)
    base = _url(org.id)

    # Second user in the same org for the release (must differ from placer).
    releaser = User(
        id=uuid.uuid4(),
        email=f"releaser-{uuid.uuid4().hex[:8]}@test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(releaser)
    db_session.flush()
    releaser.org_id = org.id
    db_session.add(OrgMembership(org_id=org.id, user_id=releaser.id, role="owner"))
    db_session.commit()

    placed = client.post(
        f"{base}/holds",
        json={"selector": {"agent_id": str(uuid.uuid4())}},
        headers=headers,
    )
    assert placed.status_code == 201, placed.text
    hold_id = placed.json()["id"]
    assert placed.json()["status"] == "active"
    assert placed.json()["placed_by"] == str(user.id)

    holds = client.get(f"{base}/holds", headers=headers).json()
    assert len(holds) == 1
    assert client.get(f"{base}/holds?status=released", headers=headers).json() == []

    # Same user cannot release their own hold.
    resp = client.post(
        f"{base}/holds/{hold_id}/release",
        json={"release_reason": "done"},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
    assert "different" in resp.text

    # Different user releases fine.
    released = client.post(
        f"{base}/holds/{hold_id}/release",
        json={"release_reason": "litigation settled"},
        headers=_auth(releaser),
    )
    assert released.status_code == 200, released.text
    data = released.json()
    assert data["status"] == "released"
    assert data["released_by"] == str(releaser.id)
    assert data["release_reason"] == "litigation settled"

    assert len(client.get(f"{base}/holds?status=released", headers=headers).json()) == 1


def test_hold_forbidden_on_pro_tier(client, db_session):
    user, org = _make_user_org(db_session, "pro", "prohold")
    resp = client.post(
        f"{_url(org.id)}/holds",
        json={"selector": {}},
        headers=_auth(user),
    )
    assert resp.status_code == 403, resp.text


# ── Events feed ──────────────────────────────────────────────────────────


def test_events_feed_lists_policy_and_hold_events(client, db_session):
    user, org = _make_user_org(db_session, "business", "events")
    headers = _auth(user)
    base = _url(org.id)

    assert client.post(f"{base}/policies", json=_policy_body(), headers=headers).status_code == 201
    assert client.post(f"{base}/holds", json={"selector": {}}, headers=headers).status_code == 201

    events = client.get(f"{base}/events", headers=headers).json()
    types = [e["event_type"] for e in events]
    assert "policy_published" in types
    assert "hold_placed" in types
    # Newest first.
    assert events == sorted(events, key=lambda e: e["created_at"], reverse=True)

    filtered = client.get(f"{base}/events?event_type=policy_published", headers=headers).json()
    assert filtered and all(e["event_type"] == "policy_published" for e in filtered)
    assert client.get(f"{base}/events?event_type=tombstone", headers=headers).json() == []


# ── Org isolation ────────────────────────────────────────────────────────


def test_cross_org_access_forbidden(client, db_session):
    user_a, org_a = _make_user_org(db_session, "business", "orga")
    _make_user_org(db_session, "business", "orgb")

    resp = client.get(f"{_url(org_a.id)}/policies", headers=_auth(user_a))
    assert resp.status_code == 200

    other_org_id = uuid.uuid4()
    resp = client.get(f"{_url(other_org_id)}/policies", headers=_auth(user_a))
    assert resp.status_code == 404  # org does not exist

    # A user from another org cannot touch org A's retention plane.
    user_b, _ = _make_user_org(db_session, "business", "orgc")
    resp = client.post(f"{_url(org_a.id)}/policies", json=_policy_body(), headers=_auth(user_b))
    assert resp.status_code == 403, resp.text
