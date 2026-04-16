"""End-to-end correlation ID tests — middleware, header propagation,
audit writer integration, and the ?correlation_id=... filter on the
audit list endpoints.
"""

import uuid

from common.audit import create_audit_entry
from common.audit.correlation import (
    resolve_correlation_id,
    to_short_id,
)
from common.models import Agent

# ── Pure helpers ─────────────────────────────────────────────────────


class TestResolveCorrelationId:
    def test_x_correlation_id_wins(self):
        cid = resolve_correlation_id("corr-abc", "req-xyz")
        assert cid == "corr-abc"

    def test_falls_back_to_x_request_id(self):
        cid = resolve_correlation_id(None, "req-xyz")
        assert cid == "req-xyz"

    def test_generates_uuid_when_absent(self):
        cid = resolve_correlation_id(None, None)
        # Should parse as a UUID
        uuid.UUID(cid)

    def test_rejects_oversized_header(self):
        """A 200-char header is ignored; we don't index arbitrary payloads."""
        cid = resolve_correlation_id("x" * 200, None)
        # Falls through to generation — verify by parsing as UUID
        uuid.UUID(cid)

    def test_rejects_empty_string(self):
        cid = resolve_correlation_id("", "")
        uuid.UUID(cid)

    def test_to_short_id(self):
        cid = "abcdef12-3456-7890-abcd-ef1234567890"
        assert to_short_id(cid) == "abcdef12"


# ── End-to-end via the test client ───────────────────────────────────


class TestMiddlewareEndToEnd:
    def test_echoes_x_correlation_id_header(self, client, auth_headers):
        """Response carries both X-Correlation-ID and X-Request-ID."""
        resp = client.get("/api/v1/audit", headers=auth_headers)
        assert resp.status_code == 200
        assert "x-correlation-id" in {h.lower() for h in resp.headers}
        assert "x-request-id" in {h.lower() for h in resp.headers}
        # The short ID is the first 8 chars of the full one
        corr = resp.headers["X-Correlation-ID"]
        short = resp.headers["X-Request-ID"]
        assert corr.startswith(short)

    def test_honors_incoming_x_correlation_id(self, client, auth_headers):
        supplied = "abcd1234-0000-4000-8000-000000000001"
        headers = {**auth_headers, "X-Correlation-ID": supplied}
        resp = client.get("/api/v1/audit", headers=headers)
        assert resp.headers["X-Correlation-ID"] == supplied

    def test_honors_x_request_id_legacy_header(self, client, auth_headers):
        """Legacy clients using X-Request-ID still trace correctly."""
        headers = {**auth_headers, "X-Request-ID": "legacy-req-xyz"}
        resp = client.get("/api/v1/audit", headers=headers)
        assert resp.headers["X-Correlation-ID"] == "legacy-req-xyz"

    def test_x_correlation_id_wins_over_x_request_id(self, client, auth_headers):
        headers = {
            **auth_headers,
            "X-Correlation-ID": "corr-wins",
            "X-Request-ID": "req-loses",
        }
        resp = client.get("/api/v1/audit", headers=headers)
        assert resp.headers["X-Correlation-ID"] == "corr-wins"


# ── Audit list filtering ─────────────────────────────────────────────


def _seed_agent_with_user(db_session, test_user):
    agent = Agent(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Corr Test Agent",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add(agent)
    db_session.commit()
    return agent


class TestAuditListCorrelationFilter:
    def test_filter_returns_only_matching_trace(self, client, db_session, test_user, auth_headers):
        """?correlation_id=X returns only rows with that exact trace."""
        agent = _seed_agent_with_user(db_session, test_user)

        trace_a = "trace-aaaa-aaaa"
        trace_b = "trace-bbbb-bbbb"

        for endpoint, trace in [
            ("/v1/alpha", trace_a),
            ("/v1/beta", trace_b),
            ("/v1/gamma", trace_a),
        ]:
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint=endpoint,
                method="POST",
                decision="allow",
                request_metadata={},
                correlation_id=trace,
            )

        resp = client.get(
            f"/api/v1/audit?correlation_id={trace_a}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        endpoints = {item["endpoint"] for item in body["items"]}
        assert endpoints == {"/v1/alpha", "/v1/gamma"}
        # All rows carry the trace in the response payload
        assert all(item["correlation_id"] == trace_a for item in body["items"])

    def test_absent_correlation_id_returns_all(self, client, db_session, test_user, auth_headers):
        agent = _seed_agent_with_user(db_session, test_user)
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/anything",
            method="POST",
            decision="allow",
            request_metadata={},
            correlation_id="some-trace",
        )
        resp = client.get("/api/v1/audit", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
