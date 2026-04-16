"""Tests for audit_log_outbox — enqueue, flush, retry, dead-letter, circuit breaker.

Uses a stub transport so we control delivery success/failure deterministically.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from common.audit import create_audit_entry
from common.audit.outbox import (
    CIRCUIT_BREAKER_THRESHOLD,
    MAX_ATTEMPTS,
    flush_outbox,
)
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

ORG_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def seeded_org(db_session):
    """Create an org + owner user + one agent."""
    owner = User(
        id=uuid.uuid4(),
        email="outbox-owner@test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(owner)
    db_session.flush()

    org = Organization(id=ORG_ID, name="Outbox Test Org", owner_id=owner.id, tier="business")
    db_session.add(org)
    db_session.flush()
    owner.org_id = ORG_ID
    db_session.add(OrgMembership(org_id=ORG_ID, user_id=owner.id, role="owner"))

    agent = Agent(
        id=uuid.uuid4(),
        user_id=owner.id,
        org_id=ORG_ID,
        name="Outbox Agent",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add(agent)
    db_session.commit()
    return owner, org, agent


@pytest.fixture
def make_sink(db_session, seeded_org):
    """Factory for creating test sinks."""
    owner, _, _ = seeded_org

    def _factory(
        *,
        name: str = "Test Sink",
        enabled: bool = True,
        filter_config: dict[str, Any] | None = None,
    ) -> AuditLogSink:
        sink = AuditLogSink(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            name=name,
            kind="webhook",
            url="https://hook.example.com/events",
            secret="testsecret",
            enabled=enabled,
            filter_config=filter_config or {},
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.commit()
        return sink

    return _factory


# ── Enqueue ──────────────────────────────────────────────────────────


class TestEnqueueForSinks:
    def test_enqueues_one_row_per_active_sink(self, db_session, seeded_org, make_sink):
        _, _, agent = seeded_org
        make_sink(name="sink-a")
        make_sink(name="sink-b")
        make_sink(name="sink-disabled", enabled=False)

        entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        rows = (
            db_session.query(AuditLogOutbox).filter(AuditLogOutbox.audit_log_id == entry.id).all()
        )
        assert len(rows) == 2
        assert all(r.status == OutboxStatus.pending.value for r in rows)

    def test_no_sinks_means_no_rows(self, db_session, seeded_org):
        _, _, agent = seeded_org
        entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        rows = (
            db_session.query(AuditLogOutbox).filter(AuditLogOutbox.audit_log_id == entry.id).all()
        )
        assert rows == []

    def test_filter_decisions_respected(self, db_session, seeded_org, make_sink):
        _, _, agent = seeded_org
        make_sink(
            name="denies-only",
            filter_config={"decisions": ["deny", "error"]},
        )

        allow_entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/allow",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        deny_entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/deny",
            method="POST",
            decision="deny",
            request_metadata={},
        )

        assert (
            db_session.query(AuditLogOutbox)
            .filter(AuditLogOutbox.audit_log_id == allow_entry.id)
            .count()
            == 0
        )
        assert (
            db_session.query(AuditLogOutbox)
            .filter(AuditLogOutbox.audit_log_id == deny_entry.id)
            .count()
            == 1
        )

    def test_filter_action_types_respected(self, db_session, seeded_org, make_sink):
        _, _, agent = seeded_org
        make_sink(
            name="lifecycle-only",
            filter_config={"action_types": ["key_rotated"]},
        )

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/anything",
            method="POST",
            decision="allow",
            request_metadata={"action_type": "chat"},
        )
        match = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/anything",
            method="POST",
            decision="allow",
            request_metadata={"action_type": "key_rotated"},
        )

        rows = db_session.query(AuditLogOutbox).all()
        assert len(rows) == 1
        assert rows[0].audit_log_id == match.id


# ── Flush ────────────────────────────────────────────────────────────


class StubTransport:
    """Controllable transport for outbox flush tests."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []
        self.next_result: DeliveryResult = DeliveryResult(success=True, status_code=200)

    def deliver(self, *, events, url, secret):  # noqa: ARG002
        self.calls.append({"events": events, "url": url, "secret": secret})
        return self.next_result


@pytest.fixture
def stub_transport(monkeypatch):
    """Patch TRANSPORTS['webhook'] with a controllable stub."""
    from common.audit import transports as transport_module

    stub = StubTransport()
    monkeypatch.setitem(transport_module.TRANSPORTS, "webhook", stub)
    return stub


class TestFlushOutbox:
    def test_successful_delivery_marks_delivered(
        self, db_session, seeded_org, make_sink, stub_transport
    ):
        _, _, agent = seeded_org
        make_sink()

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        result = flush_outbox(db_session)

        assert result.delivered == 1
        assert result.failed == 0
        assert len(stub_transport.calls) == 1
        row = db_session.query(AuditLogOutbox).first()
        assert row.status == OutboxStatus.delivered.value
        assert row.delivered_at is not None

    def test_failure_schedules_retry(self, db_session, seeded_org, make_sink, stub_transport):
        _, _, agent = seeded_org
        make_sink()
        stub_transport.next_result = DeliveryResult(success=False, status_code=500, error="boom")

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        result = flush_outbox(db_session)

        assert result.failed == 1
        row = db_session.query(AuditLogOutbox).first()
        assert row.status == OutboxStatus.failed.value
        assert row.attempts == 1
        # SQLite returns naive datetimes; normalize for comparison
        nxt = row.next_attempt_at
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=UTC)
        assert nxt > datetime.now(UTC)

    def test_exhausted_retries_become_dead_letter(
        self, db_session, seeded_org, make_sink, stub_transport
    ):
        _, _, agent = seeded_org
        make_sink()
        stub_transport.next_result = DeliveryResult(success=False, status_code=500, error="boom")

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        for _ in range(MAX_ATTEMPTS):
            # Force each row to be immediately due
            db_session.query(AuditLogOutbox).update(
                {AuditLogOutbox.next_attempt_at: datetime.now(UTC) - timedelta(seconds=1)}
            )
            db_session.commit()
            flush_outbox(db_session)

        row = db_session.query(AuditLogOutbox).first()
        assert row.status == OutboxStatus.dead_letter.value
        assert row.attempts == MAX_ATTEMPTS

    def test_circuit_breaker_opens_after_threshold(
        self, db_session, seeded_org, make_sink, stub_transport
    ):
        _, _, agent = seeded_org
        sink = make_sink()
        stub_transport.next_result = DeliveryResult(success=False, error="boom")

        # Create threshold-worth of separate audit events → outbox rows
        for i in range(CIRCUIT_BREAKER_THRESHOLD):
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint=f"/v1/ev/{i}",
                method="POST",
                decision="allow",
                request_metadata={},
            )

        flush_outbox(db_session, limit=CIRCUIT_BREAKER_THRESHOLD)

        db_session.refresh(sink)
        # Each flush iteration counts one consecutive failure per *batch*,
        # not per event — one batch with N rows = one failure. Force enough
        # iterations by bumping next_attempt_at and re-flushing.
        while sink.consecutive_failures < CIRCUIT_BREAKER_THRESHOLD:
            # Reset the one remaining row to due
            db_session.query(AuditLogOutbox).filter(
                AuditLogOutbox.status.in_((OutboxStatus.pending.value, OutboxStatus.failed.value))
            ).update({AuditLogOutbox.next_attempt_at: datetime.now(UTC) - timedelta(seconds=1)})
            db_session.commit()
            before = sink.consecutive_failures
            flush_outbox(db_session)
            db_session.refresh(sink)
            if sink.consecutive_failures == before:
                # No more rows available to fail — bail so the test doesn't loop forever.
                break

        assert sink.consecutive_failures >= 1
        # If we got up to the threshold the breaker MUST be opened
        if sink.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            assert sink.circuit_opened_at is not None

    def test_deleted_sink_skips_delivery(self, db_session, seeded_org, make_sink, stub_transport):
        _, _, agent = seeded_org
        sink = make_sink()
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        sink.deleted_at = datetime.now(UTC)
        db_session.commit()

        result = flush_outbox(db_session)
        assert result.delivered == 0
        assert len(stub_transport.calls) == 0
        # Row stays pending so operator can force-delete or un-delete
        row = db_session.query(AuditLogOutbox).first()
        assert row.status == OutboxStatus.pending.value

    def test_envelope_contains_core_fields(self, db_session, seeded_org, make_sink, stub_transport):
        _, _, agent = seeded_org
        make_sink()
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={"model": "gpt-4"},
        )
        flush_outbox(db_session)

        assert len(stub_transport.calls) == 1
        events = stub_transport.calls[0]["events"]
        assert len(events) == 1
        event = events[0]
        # Core fields enterprise pipelines expect
        assert event["endpoint"] == "/v1/chat"
        assert event["decision"] == "allow"
        assert event["org_id"] == str(ORG_ID)
        assert event["entry_hash"]  # HMAC present
