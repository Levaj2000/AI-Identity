"""Tests for /api/v1/audit/sinks — CRUD, access control, secret rotation, test delivery."""

from __future__ import annotations

import uuid

import pytest

from common.audit.transports import DeliveryResult
from common.models import (
    Agent,
    AuditLogOutbox,
    AuditLogSink,
    Organization,
    OrgMembership,
    OutboxStatus,
    User,
)

ORG_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
OWNER_EMAIL = "sinks-owner@test"
MEMBER_EMAIL = "sinks-member@test"


@pytest.fixture
def seeded(db_session):
    """Org with one owner, one plain member, one agent owned by the owner."""
    owner = User(
        id=uuid.uuid4(),
        email=OWNER_EMAIL,
        role="owner",
        tier="enterprise",
    )
    member = User(
        id=uuid.uuid4(),
        email=MEMBER_EMAIL,
        role="owner",
        tier="enterprise",
    )
    db_session.add_all([owner, member])
    db_session.flush()

    org = Organization(id=ORG_ID, name="Sinks Test Org", owner_id=owner.id, tier="business")
    db_session.add(org)
    db_session.flush()

    owner.org_id = ORG_ID
    member.org_id = ORG_ID
    db_session.add_all(
        [
            OrgMembership(org_id=ORG_ID, user_id=owner.id, role="owner"),
            OrgMembership(org_id=ORG_ID, user_id=member.id, role="member"),
        ]
    )
    agent = Agent(
        id=uuid.uuid4(),
        user_id=owner.id,
        org_id=ORG_ID,
        name="a",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add(agent)
    db_session.commit()
    return owner, member, org, agent


@pytest.fixture
def stub_transport(monkeypatch):
    from common.audit import transports as transport_module

    class Stub:
        next_result = DeliveryResult(success=True, status_code=200, latency_ms=5)

        def deliver(self, *, events, url, secret):  # noqa: ARG002
            return self.next_result

    stub = Stub()
    monkeypatch.setitem(transport_module.TRANSPORTS, "webhook", stub)
    return stub


# ── Create ───────────────────────────────────────────────────────────


class TestCreate:
    def test_owner_can_create_and_receives_secret(self, client, seeded):
        resp = client.post(
            "/api/v1/audit/sinks",
            headers={"X-API-Key": OWNER_EMAIL},
            json={
                "name": "Splunk HEC Prod",
                "url": "https://splunk.example.com/services/collector",
                "description": "Cisco SOC feed",
                "filter": {"decisions": ["deny", "error"]},
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Splunk HEC Prod"
        # Secret is returned on create only
        assert body["secret"] and len(body["secret"]) >= 32
        assert body["enabled"] is True
        assert body["filter"]["decisions"] == ["deny", "error"]

    def test_http_url_rejected(self, client, seeded):
        resp = client.post(
            "/api/v1/audit/sinks",
            headers={"X-API-Key": OWNER_EMAIL},
            json={"name": "bad", "url": "http://insecure.example.com/hook"},
        )
        assert resp.status_code == 422

    def test_member_cannot_create(self, client, seeded):
        resp = client.post(
            "/api/v1/audit/sinks",
            headers={"X-API-Key": MEMBER_EMAIL},
            json={"name": "x", "url": "https://hook.example.com/h"},
        )
        assert resp.status_code == 403


# ── List ─────────────────────────────────────────────────────────────


class TestList:
    def test_owner_sees_only_own_org(self, client, db_session, seeded):
        owner, _, _, _ = seeded
        db_session.add(
            AuditLogSink(
                org_id=ORG_ID,
                name="mine",
                url="https://a.example.com/h",
                secret="s" * 32,
                created_by=owner.id,
            )
        )
        # An unrelated org with its own sink
        other_owner = User(
            id=uuid.uuid4(),
            email="other-org@test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(other_owner)
        db_session.flush()
        other_org_id = uuid.uuid4()
        db_session.add(
            Organization(
                id=other_org_id,
                name="Other Org",
                owner_id=other_owner.id,
                tier="business",
            )
        )
        db_session.flush()
        db_session.add(
            AuditLogSink(
                org_id=other_org_id,
                name="theirs",
                url="https://b.example.com/h",
                secret="s" * 32,
                created_by=other_owner.id,
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/audit/sinks", headers={"X-API-Key": OWNER_EMAIL})
        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["items"]]
        assert names == ["mine"]

    def test_secret_never_returned_on_list(self, client, db_session, seeded):
        owner, _, _, _ = seeded
        db_session.add(
            AuditLogSink(
                org_id=ORG_ID,
                name="x",
                url="https://a.example.com/h",
                secret="plaintext-secret",
                created_by=owner.id,
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/audit/sinks", headers={"X-API-Key": OWNER_EMAIL})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "secret" not in item


# ── Update ───────────────────────────────────────────────────────────


class TestUpdate:
    def test_rotate_secret_returns_new_value(self, client, db_session, seeded):
        owner, _, _, _ = seeded
        sink = AuditLogSink(
            org_id=ORG_ID,
            name="x",
            url="https://a.example.com/h",
            secret="oldsecret" * 4,
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.commit()

        resp = client.patch(
            f"/api/v1/audit/sinks/{sink.id}",
            headers={"X-API-Key": OWNER_EMAIL},
            json={"rotate_secret": True},
        )
        assert resp.status_code == 200
        new_secret = resp.json()["secret"]
        assert new_secret and new_secret != ("oldsecret" * 4)

        # Verify DB got the new secret
        db_session.refresh(sink)
        assert sink.secret == new_secret

    def test_enable_resets_circuit_breaker(self, client, db_session, seeded):
        owner, _, _, _ = seeded
        import datetime as _dt

        sink = AuditLogSink(
            org_id=ORG_ID,
            name="x",
            url="https://a.example.com/h",
            secret="s" * 32,
            enabled=False,
            consecutive_failures=15,
            circuit_opened_at=_dt.datetime.now(_dt.UTC),
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.commit()

        resp = client.patch(
            f"/api/v1/audit/sinks/{sink.id}",
            headers={"X-API-Key": OWNER_EMAIL},
            json={"enabled": True},
        )
        assert resp.status_code == 200
        db_session.refresh(sink)
        assert sink.enabled is True
        assert sink.consecutive_failures == 0
        assert sink.circuit_opened_at is None

    def test_cross_org_update_returns_404(self, client, db_session, seeded):
        # A sink in a different org
        other_owner = User(id=uuid.uuid4(), email="oo@test", role="owner", tier="enterprise")
        db_session.add(other_owner)
        db_session.flush()
        other_org = Organization(id=uuid.uuid4(), name="Oo", owner_id=other_owner.id, tier="free")
        db_session.add(other_org)
        db_session.flush()
        sink = AuditLogSink(
            org_id=other_org.id,
            name="x",
            url="https://a.example.com/h",
            secret="s" * 32,
            created_by=other_owner.id,
        )
        db_session.add(sink)
        db_session.commit()

        resp = client.patch(
            f"/api/v1/audit/sinks/{sink.id}",
            headers={"X-API-Key": OWNER_EMAIL},
            json={"name": "haha"},
        )
        assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────


class TestDelete:
    def test_delete_with_pending_rows_requires_force(self, client, db_session, seeded):
        owner, _, _, agent = seeded
        sink = AuditLogSink(
            org_id=ORG_ID,
            name="x",
            url="https://a.example.com/h",
            secret="s" * 32,
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.flush()
        # Write an audit entry with this sink active so an outbox row is created.
        from common.audit import create_audit_entry

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        resp = client.delete(
            f"/api/v1/audit/sinks/{sink.id}",
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 409
        # API wraps HTTPException.detail in {"error": {"message": ...}}
        assert "pending" in resp.json()["error"]["message"].lower()

        resp2 = client.delete(
            f"/api/v1/audit/sinks/{sink.id}?force=true",
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp2.status_code == 204

        # Sink soft-deleted
        db_session.refresh(sink)
        assert sink.deleted_at is not None
        assert sink.enabled is False

        # Pending outbox rows became dead_letter
        rows = db_session.query(AuditLogOutbox).filter(AuditLogOutbox.sink_id == sink.id).all()
        assert all(r.status == OutboxStatus.dead_letter.value for r in rows)


# ── Test delivery ────────────────────────────────────────────────────


class TestTestDelivery:
    def test_test_endpoint_invokes_transport(self, client, db_session, seeded, stub_transport):
        owner, _, _, _ = seeded
        sink = AuditLogSink(
            org_id=ORG_ID,
            name="x",
            url="https://a.example.com/h",
            secret="s" * 32,
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.commit()

        resp = client.post(
            f"/api/v1/audit/sinks/{sink.id}/test",
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["delivered"] is True
        assert body["status_code"] == 200

    def test_failed_delivery_surfaces_error(self, client, db_session, seeded, stub_transport):
        owner, _, _, _ = seeded
        sink = AuditLogSink(
            org_id=ORG_ID,
            name="x",
            url="https://a.example.com/h",
            secret="s" * 32,
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.commit()

        stub_transport.next_result = DeliveryResult(
            success=False, status_code=500, error="upstream boom", latency_ms=12
        )
        resp = client.post(
            f"/api/v1/audit/sinks/{sink.id}/test",
            headers={"X-API-Key": OWNER_EMAIL},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["delivered"] is False
        assert body["status_code"] == 500
        assert "boom" in body["error"]
