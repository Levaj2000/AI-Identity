"""Tests for /api/v1/audit/summarize — guarantee numeric facts are grounded.

The bug being defended: the AI summarizer used to let the LLM produce both
the facts (counts, time window) and the narrative. When the LLM lacked an
aggregate to read, it would hallucinate plausible-looking numbers — leading
to the AI panel and the KPI bar showing contradictory totals on the same
screen (see bug report 2026-05-12, "ada-dogfood" investor demo).

The fix: numeric facts are computed deterministically server-side from the
same query as the KPI bar (`_compute_stats`), and returned in a dedicated
`facts` block on the response. The LLM only writes prose around those facts
and is forbidden from producing observed_facts rows; the server overrides
that field with its own values.

These tests assert that contract holds even when the LLM tries to fight it.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from common.audit import create_audit_entry


@pytest.fixture
def perplexity_enabled(monkeypatch):
    """Pretend Perplexity is configured so the route gets past the 503 gate."""
    from common.config.settings import settings

    monkeypatch.setattr(settings, "perplexity_api_key", "test-key-not-used")
    yield


def _llm_report(
    title="Test summary",
    executive_summary="Executive prose.",
    observed_facts=None,
    assessment="Assessment prose.",
    follow_ups=None,
    risk_level="informational",
    confidence="medium",
):
    """Build a fixture LLM response. Defaults to a well-behaved (empty) facts list."""
    return {
        "title": title,
        "executive_summary": executive_summary,
        "observed_facts": observed_facts if observed_facts is not None else [],
        "assessment": assessment,
        "recommended_follow_ups": follow_ups or [],
        "risk_level": risk_level,
        "confidence": confidence,
    }


def _create_agent(client, auth_headers, name="Summarize Test Agent"):
    resp = client.post("/api/v1/agents", headers=auth_headers, json={"name": name})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["agent"]["id"]


def _seed_known_window(db_session, agent_id, *, allows=17, denies=1, errors=0):
    """Seed an audit window with known counts.

    Matches the bug report's screenshot: 17 allow + 1 deny + 0 error = 18 total.
    `create_audit_entry` stamps created_at = now() internally, so we rely on
    a wide filter window (1 year ± now) in the tests to capture them all.
    """
    for _ in range(allows):
        create_audit_entry(
            db_session,
            agent_id=uuid.UUID(agent_id),
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
        )
    for _ in range(denies):
        create_audit_entry(
            db_session,
            agent_id=uuid.UUID(agent_id),
            endpoint="/v1/embeddings",
            method="POST",
            decision="deny",
        )
    for _ in range(errors):
        create_audit_entry(
            db_session,
            agent_id=uuid.UUID(agent_id),
            endpoint="/v1/chat",
            method="POST",
            decision="error",
        )
    return datetime.now(UTC)


# ── Mode 1: "Explain N visible events" with a filter window ─────────────


class TestModeOneFilterWindow:
    """When the user gives a filter window, facts must match the KPI bar exactly."""

    def test_facts_match_kpi_bar(self, client, auth_headers, db_session, perplexity_enabled):
        """The deterministic facts in /summarize must equal /audit/stats counts."""
        agent_id = _create_agent(client, auth_headers)
        base = _seed_known_window(db_session, agent_id, allows=17, denies=1, errors=0)

        start = (base - timedelta(days=365)).isoformat()
        end = (base + timedelta(days=365)).isoformat()

        # Reference: what the KPI bar would show for this filter.
        stats_resp = client.get(
            "/api/v1/audit/stats",
            headers=auth_headers,
            params={"agent_id": agent_id, "start_date": start, "end_date": end},
        )
        assert stats_resp.status_code == 200
        kpi = stats_resp.json()

        # The KPI bar should match the seed values plus 1 audit row that
        # /api/v1/agents creates as a side effect of agent creation. The
        # important contract is that the panel and the KPI bar agree —
        # whatever the KPI bar says, the panel must say the same.
        assert kpi["total_events"] == 19
        assert kpi["allowed_count"] == 18
        assert kpi["denied_count"] == 1
        assert kpi["error_count"] == 0

        # Now ask the summarize endpoint. The LLM is mocked to return a benign
        # report — facts must come from the server, not from this fixture.
        with patch(
            "api.app.services.perplexity.summarize_audit_events",
            return_value=_llm_report(),
        ):
            resp = client.post(
                "/api/v1/audit/summarize",
                headers=auth_headers,
                json={
                    "agent_id": agent_id,
                    "start_date": start,
                    "end_date": end,
                    "max_events": 100,
                },
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Authoritative numeric facts must match the KPI bar byte-for-byte.
        assert data["facts"]["total_requests"] == kpi["total_events"]
        assert data["facts"]["requests_allowed"] == kpi["allowed_count"]
        assert data["facts"]["requests_denied"] == kpi["denied_count"]
        assert data["facts"]["errors"] == kpi["error_count"]
        assert data["facts"]["aggregate_window_source"] == "filter"

    def test_observed_facts_strictly_overrides_llm(
        self, client, auth_headers, db_session, perplexity_enabled
    ):
        """Even if the LLM emits its own observed_facts, the server overrides them.

        This is the regression guard for the original bug: the panel showed
        182/113/69 because the LLM invented those numbers. We verify here
        that whatever the LLM emits in observed_facts is discarded.
        """
        agent_id = _create_agent(client, auth_headers)
        base = _seed_known_window(db_session, agent_id, allows=17, denies=1, errors=0)
        start = (base - timedelta(days=365)).isoformat()
        end = (base + timedelta(days=365)).isoformat()

        adversarial = _llm_report(
            observed_facts=[
                {"label": "Total requests", "value": "182"},
                {"label": "Requests allowed", "value": "113"},
                {"label": "Requests denied", "value": "69"},
                {"label": "Errors", "value": "0"},
            ],
        )
        with patch(
            "api.app.services.perplexity.summarize_audit_events",
            return_value=adversarial,
        ):
            resp = client.post(
                "/api/v1/audit/summarize",
                headers=auth_headers,
                json={
                    "agent_id": agent_id,
                    "start_date": start,
                    "end_date": end,
                    "max_events": 100,
                },
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        observed = {f["label"]: f["value"] for f in data["observed_facts"]}
        # Hallucinated numbers (the 182/113/69 from the bug report) must NOT appear.
        # Real counts: 17 allow + 1 deny + 1 from agent-creation audit row = 19.
        assert observed["Total requests"] == "19"
        assert observed["Total requests"] != "182"
        assert observed["Requests allowed"] == "18"
        assert observed["Requests allowed"] != "113"
        assert observed["Requests denied"] == "1"
        assert observed["Requests denied"] != "69"
        assert observed["Errors"] == "0"


# ── Mode 2: Single-event analysis with no filter window ─────────────────


class TestModeTwoSingleEvent:
    """Single-event drilldown: aggregates come from a ±24h neighborhood."""

    def test_event_neighborhood_window(self, client, auth_headers, db_session, perplexity_enabled):
        """event_ids with no filter window → ±24h neighborhood around the event."""
        agent_id = _create_agent(client, auth_headers)
        _seed_known_window(db_session, agent_id, allows=17, denies=1, errors=0)

        # Pick the single deny event to drill into.
        from common.models import AuditLog

        deny = (
            db_session.query(AuditLog)
            .filter(AuditLog.agent_id == uuid.UUID(agent_id), AuditLog.decision == "deny")
            .first()
        )
        assert deny is not None

        with patch(
            "api.app.services.perplexity.summarize_audit_events",
            return_value=_llm_report(),
        ):
            resp = client.post(
                "/api/v1/audit/summarize",
                headers=auth_headers,
                json={"event_ids": [deny.id], "max_events": 1},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["facts"]["aggregate_window_source"] == "event_neighborhood"
        # All 18 events fall inside a 48h neighborhood around the deny.
        # Agent-creation audit entry adds 1 to the total.
        assert data["facts"]["total_requests"] >= 18
        assert data["facts"]["requests_denied"] == 1
        assert data["facts"]["time_window_start"] is not None
        assert data["facts"]["time_window_end"] is not None

    def test_no_hallucinated_digits_for_single_event(
        self, client, auth_headers, db_session, perplexity_enabled
    ):
        """Even with an adversarial LLM, single-event drilldown shows real counts."""
        agent_id = _create_agent(client, auth_headers)
        _seed_known_window(db_session, agent_id, allows=17, denies=1, errors=0)

        from common.models import AuditLog

        deny = (
            db_session.query(AuditLog)
            .filter(AuditLog.agent_id == uuid.UUID(agent_id), AuditLog.decision == "deny")
            .first()
        )

        adversarial = _llm_report(
            observed_facts=[
                {"label": "Total requests", "value": "182"},
                {"label": "Requests allowed", "value": "113"},
                {"label": "Requests denied", "value": "69"},
                {"label": "Errors", "value": "0"},
            ],
            assessment="high deny rate (38%) warrants review",
        )
        with patch(
            "api.app.services.perplexity.summarize_audit_events",
            return_value=adversarial,
        ):
            resp = client.post(
                "/api/v1/audit/summarize",
                headers=auth_headers,
                json={"event_ids": [deny.id], "max_events": 1},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        observed = {f["label"]: f["value"] for f in data["observed_facts"]}
        # Critically: the hallucinated 182/113/69 must not surface.
        assert observed["Total requests"] != "182"
        assert observed["Requests denied"] != "69"
        # Real denied count is 1.
        assert observed["Requests denied"] == "1"


# ── Stability across LLM seeds ──────────────────────────────────────────


class TestStabilityAcrossLlmRuns:
    """The facts block must be identical across different LLM outputs."""

    def test_facts_byte_identical_across_llm_outputs(
        self, client, auth_headers, db_session, perplexity_enabled
    ):
        agent_id = _create_agent(client, auth_headers)
        base = _seed_known_window(db_session, agent_id, allows=17, denies=1, errors=0)
        start = (base - timedelta(days=365)).isoformat()
        end = (base + timedelta(days=365)).isoformat()
        body = {
            "agent_id": agent_id,
            "start_date": start,
            "end_date": end,
            "max_events": 100,
        }

        observed_facts_list: list[list[dict]] = []
        for variant_idx in range(5):
            variant = _llm_report(
                title=f"Variant {variant_idx}",
                executive_summary=f"Prose variant #{variant_idx} with different wording.",
                observed_facts=[
                    {"label": "garbage", "value": str(variant_idx * 9999)},
                ],
                assessment=f"Assessment {variant_idx}",
                risk_level="medium" if variant_idx % 2 else "informational",
            )
            with patch(
                "api.app.services.perplexity.summarize_audit_events",
                return_value=variant,
            ):
                resp = client.post("/api/v1/audit/summarize", headers=auth_headers, json=body)
            assert resp.status_code == 200, resp.text
            data = resp.json()
            observed_facts_list.append(data["observed_facts"])

        # Every run must produce the exact same observed_facts table.
        first = observed_facts_list[0]
        for other in observed_facts_list[1:]:
            assert other == first
