"""Tests for Prometheus metrics — auth, counters, gauges, scrape handler."""

from __future__ import annotations

import uuid

from prometheus_client.parser import text_string_to_metric_families

from common.audit import create_audit_entry
from common.audit.outbox import flush_outbox
from common.audit.transports import DeliveryResult
from common.config.settings import settings
from common.models import Agent, AuditLogSink, Organization, OrgMembership, User
from common.observability.metrics import (
    REGISTRY,
    audit_denies_total,
    audit_events_total,
    record_audit_write,
    refresh_db_gauges,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _scrape(client, internal_key: str | None = None):
    """Fetch /metrics with the given internal key (defaults to the configured one)."""
    key = internal_key if internal_key is not None else settings.internal_service_key
    return client.get("/metrics", headers={"X-Internal-Key": key} if key else {})


def _metric_value(body: str, name: str, **labels) -> float | None:
    """Pull a metric value from a Prometheus exposition body.

    Returns None if the metric/label combination isn't present.
    """
    for family in text_string_to_metric_families(body):
        if family.name != name:
            continue
        for sample in family.samples:
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                return sample.value
    return None


def _counter_value(name: str, **labels) -> float:
    """Read a counter/histogram directly from the in-process registry.

    Searches by *sample* name (e.g. ``..._total`` for counters, ``..._count``
    for histograms), not by the metric family name (which prometheus_client
    strips the ``_total`` suffix from internally).
    """
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name != name:
                continue
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                return sample.value
    return 0.0


# ── Auth on /metrics ────────────────────────────────────────────────


class TestMetricsAuth:
    def test_missing_key_returns_401(self, client, monkeypatch):
        monkeypatch.setattr(settings, "internal_service_key", "testkey")
        resp = client.get("/metrics")
        assert resp.status_code == 401

    def test_wrong_key_returns_401(self, client, monkeypatch):
        monkeypatch.setattr(settings, "internal_service_key", "testkey")
        resp = client.get("/metrics", headers={"X-Internal-Key": "nope"})
        assert resp.status_code == 401

    def test_correct_key_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(settings, "internal_service_key", "testkey")
        resp = client.get("/metrics", headers={"X-Internal-Key": "testkey"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")

    def test_unconfigured_service_key_rejects_all(self, client, monkeypatch):
        """With no internal_service_key set, every request is unauthorized."""
        monkeypatch.setattr(settings, "internal_service_key", "")
        resp = client.get("/metrics", headers={"X-Internal-Key": "anything"})
        assert resp.status_code == 401


# ── Counter emission from writer ────────────────────────────────────


class TestAuditCountersFromWriter:
    def _seed_agent(self, db_session):
        user = User(id=uuid.uuid4(), email="metrics-user@test", role="owner", tier="enterprise")
        db_session.add(user)
        db_session.flush()
        agent = Agent(
            id=uuid.uuid4(),
            user_id=user.id,
            name="m",
            status="active",
            capabilities=[],
            metadata_={},
        )
        db_session.add(agent)
        db_session.commit()
        return agent

    def test_write_increments_events_counter(self, db_session):
        agent = self._seed_agent(db_session)
        before = _counter_value("ai_identity_audit_events_total", decision="allow")

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/x",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        after = _counter_value("ai_identity_audit_events_total", decision="allow")
        assert after == before + 1

    def test_deny_reason_counter_tracks_separately(self, db_session):
        agent = self._seed_agent(db_session)
        before = _counter_value("ai_identity_audit_denies_total", reason="policy_not_found")

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/x",
            method="POST",
            decision="deny",
            request_metadata={"deny_reason": "policy_not_found"},
        )

        after = _counter_value("ai_identity_audit_denies_total", reason="policy_not_found")
        assert after == before + 1

    def test_latency_histogram_records_observation(self, db_session):
        agent = self._seed_agent(db_session)
        before = _counter_value("ai_identity_audit_latency_ms_count")

        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/x",
            method="POST",
            decision="allow",
            request_metadata={},
            latency_ms=42,
        )

        after = _counter_value("ai_identity_audit_latency_ms_count")
        assert after == before + 1


# ── Outbox counter emission ─────────────────────────────────────────


class TestOutboxDeliveryCounters:
    def _seed(self, db_session):
        owner = User(
            id=uuid.uuid4(),
            email="outbox-metrics-owner@test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(owner)
        db_session.flush()

        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="OM Org", owner_id=owner.id, tier="business")
        db_session.add(org)
        db_session.flush()
        owner.org_id = org_id
        db_session.add(OrgMembership(org_id=org_id, user_id=owner.id, role="owner"))

        agent = Agent(
            id=uuid.uuid4(),
            user_id=owner.id,
            org_id=org_id,
            name="a",
            status="active",
            capabilities=[],
            metadata_={},
        )
        db_session.add(agent)

        sink = AuditLogSink(
            org_id=org_id,
            name="x",
            url="https://hook.example.com/h",
            secret="s" * 32,
            created_by=owner.id,
        )
        db_session.add(sink)
        db_session.commit()
        return owner, org, agent, sink

    def test_delivered_bumps_delivered_counter(self, db_session, monkeypatch):
        from common.audit import transports as tm

        class OKStub:
            def deliver(self, *, events, url, secret):  # noqa: ARG002
                return DeliveryResult(success=True, status_code=200)

        monkeypatch.setitem(tm.TRANSPORTS, "webhook", OKStub())

        _, _, agent, _ = self._seed(db_session)
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/a",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        before = _counter_value("ai_identity_outbox_deliveries_total", outcome="delivered")
        flush_outbox(db_session)
        after = _counter_value("ai_identity_outbox_deliveries_total", outcome="delivered")
        assert after == before + 1


# ── DB-backed gauges ────────────────────────────────────────────────


class TestRefreshDbGauges:
    def test_gauges_reflect_live_counts(self, db_session, client, monkeypatch):
        monkeypatch.setattr(settings, "internal_service_key", "k")

        user = User(
            id=uuid.uuid4(),
            email="gauge-user@test",
            role="owner",
            tier="enterprise",
        )
        db_session.add(user)
        db_session.flush()
        db_session.add(
            Agent(
                id=uuid.uuid4(),
                user_id=user.id,
                name="a1",
                status="active",
                capabilities=[],
                metadata_={},
            )
        )
        db_session.add(
            Agent(
                id=uuid.uuid4(),
                user_id=user.id,
                name="a2",
                status="suspended",
                capabilities=[],
                metadata_={},
            )
        )
        db_session.commit()

        resp = client.get("/metrics", headers={"X-Internal-Key": "k"})
        assert resp.status_code == 200
        body = resp.text

        assert _metric_value(body, "ai_identity_agents_total", status="active") == 1
        assert _metric_value(body, "ai_identity_agents_total", status="suspended") == 1


# ── Graceful degradation ────────────────────────────────────────────


class TestMetricsResilience:
    def test_record_audit_write_never_raises(self):
        """Broken labels/values must not kill the caller."""
        # Normal case
        record_audit_write(decision="allow", latency_ms=10)
        # Weird but defensible input — should be swallowed
        record_audit_write(decision="allow", latency_ms=-1)  # negative ignored
        # Explicit None latency
        record_audit_write(decision="deny", deny_reason="x", latency_ms=None)

    def test_refresh_gauges_swallows_db_errors(self, db_session):
        """A broken DB doesn't kill the scrape."""

        class BrokenDB:
            def execute(self, *a, **kw):  # noqa: ANN002, ARG002
                raise RuntimeError("simulated db outage")

        # Must not raise
        refresh_db_gauges(BrokenDB())


# ── Counter-value sanity check (paranoia) ───────────────────────────


class TestCollectorsAreRegistered:
    def test_expected_metrics_appear_in_registry(self, client, monkeypatch):
        monkeypatch.setattr(settings, "internal_service_key", "k")
        # Ensure at least one label instance exists so the family renders
        audit_events_total.labels(decision="allow").inc(0)
        audit_denies_total.labels(reason="n/a").inc(0)

        resp = client.get("/metrics", headers={"X-Internal-Key": "k"})
        assert resp.status_code == 200
        body = resp.text

        for name in (
            "ai_identity_audit_events_total",
            "ai_identity_audit_denies_total",
            "ai_identity_audit_latency_ms",
            "ai_identity_outbox_deliveries_total",
            "ai_identity_agents_total",
            "ai_identity_organizations_total",
            "ai_identity_outbox_backlog",
            "ai_identity_sinks_total",
            "ai_identity_sinks_circuit_open",
        ):
            assert name in body, f"expected metric {name!r} in exposition output"
