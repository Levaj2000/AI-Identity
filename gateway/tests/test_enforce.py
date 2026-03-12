"""Tests for fail-closed gateway enforcement.

SECURITY-CRITICAL: These tests verify that the gateway denies requests
when anything goes wrong — timeout, error, no policy, circuit breaker open.
Only an explicit ALLOW from a successful policy evaluation permits a request.

Acceptance criteria from Sprint #45:
  - Policy engine down = 503
  - Timeout = denied
  - Circuit breaker triggers after 5 consecutive failures
"""

import uuid
from unittest.mock import patch

import pytest

from common.models import AuditLog, Policy
from gateway.app.circuit_breaker import CircuitState
from gateway.app.enforce import (
    Decision,
    DenyReason,
    _endpoint_matches,
    _evaluate_policy_rules,
    enforce,
    policy_circuit_breaker,
)

# Fixed UUIDs
AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
MISSING_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-999999999999")


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    """Reset the module-level circuit breaker between tests."""
    policy_circuit_breaker.reset()
    yield
    policy_circuit_breaker.reset()


# ── Endpoint Matching ──────────────────────────────────────────────────


class TestEndpointMatching:
    """Verify the endpoint pattern matching logic."""

    def test_exact_match(self):
        assert _endpoint_matches("/v1/chat", "/v1/chat") is True
        assert _endpoint_matches("/v1/chat", "/v1/embeddings") is False

    def test_wildcard_all(self):
        assert _endpoint_matches("/v1/chat", "*") is True
        assert _endpoint_matches("/anything", "*") is True

    def test_prefix_wildcard(self):
        assert _endpoint_matches("/v1/chat", "/v1/*") is True
        assert _endpoint_matches("/v1/embeddings", "/v1/*") is True
        assert _endpoint_matches("/v2/chat", "/v1/*") is False

    def test_prefix_wildcard_exact_parent(self):
        """'/v1/*' also matches '/v1' exactly."""
        assert _endpoint_matches("/v1", "/v1/*") is True


# ── Policy Rule Evaluation ─────────────────────────────────────────────


class TestPolicyRuleEvaluation:
    """Verify the policy rule engine — fail-closed by default."""

    def test_empty_rules_deny(self):
        """Empty rules dict = no permissions = DENY."""
        assert _evaluate_policy_rules({}, "/v1/chat", "POST") is False

    def test_no_allowed_endpoints_deny(self):
        """Rules without allowed_endpoints = DENY (fail-closed)."""
        rules = {"allowed_methods": ["POST"]}
        assert _evaluate_policy_rules(rules, "/v1/chat", "POST") is False

    def test_allowed_endpoint_and_method(self):
        """Matching endpoint + method = ALLOW."""
        rules = {
            "allowed_endpoints": ["/v1/*"],
            "allowed_methods": ["POST"],
        }
        assert _evaluate_policy_rules(rules, "/v1/chat", "POST") is True

    def test_allowed_endpoint_wrong_method(self):
        """Matching endpoint but wrong method = DENY."""
        rules = {
            "allowed_endpoints": ["/v1/*"],
            "allowed_methods": ["GET"],
        }
        assert _evaluate_policy_rules(rules, "/v1/chat", "POST") is False

    def test_no_method_restriction_allows_all(self):
        """No allowed_methods specified = any method is fine (if endpoint matches)."""
        rules = {"allowed_endpoints": ["/v1/*"]}
        assert _evaluate_policy_rules(rules, "/v1/chat", "POST") is True
        assert _evaluate_policy_rules(rules, "/v1/chat", "DELETE") is True

    def test_denied_endpoint_overrides_allow(self):
        """Explicit deny takes precedence over allow."""
        rules = {
            "allowed_endpoints": ["/v1/*"],
            "denied_endpoints": ["/v1/admin"],
        }
        assert _evaluate_policy_rules(rules, "/v1/chat", "POST") is True
        assert _evaluate_policy_rules(rules, "/v1/admin", "POST") is False

    def test_multiple_allowed_endpoints(self):
        """Multiple allowed patterns — any match = ALLOW."""
        rules = {
            "allowed_endpoints": ["/v1/chat", "/v1/embeddings"],
        }
        assert _evaluate_policy_rules(rules, "/v1/chat", "POST") is True
        assert _evaluate_policy_rules(rules, "/v1/embeddings", "POST") is True
        assert _evaluate_policy_rules(rules, "/v1/admin", "POST") is False


# ── Enforcement — Happy Path ───────────────────────────────────────────


class TestEnforceAllow:
    """Verify that requests are allowed when policy explicitly permits them."""

    def test_allow_with_matching_policy(self, db_session, test_agent, test_policy):
        """Agent with active policy allowing /v1/* → ALLOW."""
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        assert result.allowed is True
        assert result.decision == Decision.ALLOW
        assert result.status_code == 200
        assert result.deny_reason is None

    def test_allow_creates_audit_entry(self, db_session, test_agent, test_policy):
        """Allowed requests are logged in the audit trail."""
        enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        entries = db_session.query(AuditLog).all()
        assert len(entries) == 1
        assert entries[0].decision == "allow"
        assert entries[0].agent_id == test_agent.id
        assert entries[0].endpoint == "/v1/chat"


# ── Enforcement — Fail-Closed ──────────────────────────────────────────


class TestEnforceFailClosed:
    """SECURITY: Verify that the gateway DENIES on every failure mode."""

    def test_deny_agent_not_found(self, db_session):
        """Unknown agent = DENY (404)."""
        result = enforce(
            db_session,
            agent_id=MISSING_AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
        )

        assert result.allowed is False
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.AGENT_NOT_FOUND
        assert result.status_code == 404

    def test_deny_agent_suspended(self, db_session, suspended_agent):
        """Suspended agent = DENY (403)."""
        result = enforce(
            db_session,
            agent_id=suspended_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        assert result.allowed is False
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.AGENT_INACTIVE
        assert result.status_code == 403

    def test_deny_no_active_policy(self, db_session, test_agent):
        """Agent with no active policy = DENY (fail-closed)."""
        # Agent exists but has no policy
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        assert result.allowed is False
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.NO_ACTIVE_POLICY
        assert result.status_code == 403

    def test_deny_policy_rejects_endpoint(self, db_session, test_agent, test_policy):
        """Policy that doesn't allow the endpoint = DENY."""
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v2/admin",  # Not in /v1/* allowed pattern
            method="POST",
        )

        assert result.allowed is False
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.POLICY_DENIED
        assert result.status_code == 403

    def test_deny_policy_rejects_method(self, db_session, test_agent):
        """Policy that doesn't allow the method = DENY."""
        # Policy only allows GET
        policy = Policy(
            agent_id=test_agent.id,
            rules={
                "allowed_endpoints": ["/v1/*"],
                "allowed_methods": ["GET"],
            },
            version=1,
            is_active=True,
        )
        db_session.add(policy)
        db_session.commit()

        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",  # Not allowed
        )

        assert result.allowed is False
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.POLICY_DENIED

    def test_deny_creates_audit_entry(self, db_session, test_agent):
        """Denied requests are logged in the audit trail."""
        enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        entries = db_session.query(AuditLog).all()
        assert len(entries) == 1
        assert entries[0].decision == "deny"
        assert entries[0].request_metadata.get("deny_reason") == "no_active_policy"


# ── Enforcement — Policy Errors ────────────────────────────────────────


class TestEnforcePolicyErrors:
    """Verify fail-closed on policy evaluation errors and timeouts."""

    def test_deny_on_policy_evaluation_error(self, db_session, test_agent, test_policy):
        """Exception during policy evaluation = DENY + record failure."""
        with patch(
            "gateway.app.enforce._load_and_evaluate_policy",
            side_effect=RuntimeError("DB connection lost"),
        ):
            result = enforce(
                db_session,
                agent_id=test_agent.id,
                endpoint="/v1/chat",
                method="POST",
            )

        assert result.allowed is False
        assert result.decision == Decision.ERROR
        assert result.deny_reason == DenyReason.POLICY_ERROR
        assert result.status_code == 503

    def test_deny_on_policy_timeout(self, db_session, test_agent, test_policy):
        """Policy evaluation exceeding timeout = DENY + record failure."""
        from concurrent.futures import TimeoutError

        with patch("gateway.app.enforce._policy_executor") as mock_executor:
            mock_future = mock_executor.submit.return_value
            mock_future.result.side_effect = TimeoutError()

            result = enforce(
                db_session,
                agent_id=test_agent.id,
                endpoint="/v1/chat",
                method="POST",
            )

        assert result.allowed is False
        assert result.decision == Decision.ERROR
        assert result.deny_reason == DenyReason.POLICY_TIMEOUT
        assert result.status_code == 503

    def test_error_creates_audit_entry(self, db_session, test_agent, test_policy):
        """Policy errors are logged in the audit trail."""
        with patch(
            "gateway.app.enforce._load_and_evaluate_policy",
            side_effect=RuntimeError("DB down"),
        ):
            enforce(
                db_session,
                agent_id=test_agent.id,
                endpoint="/v1/chat",
                method="POST",
            )

        entries = db_session.query(AuditLog).all()
        assert len(entries) == 1
        assert entries[0].decision == "error"
        assert entries[0].request_metadata.get("deny_reason") == "policy_eval_error"


# ── Circuit Breaker Integration ────────────────────────────────────────


class TestEnforceCircuitBreaker:
    """Verify circuit breaker trips after repeated failures and denies all."""

    def test_circuit_breaker_trips_after_threshold(self, db_session, test_agent, test_policy):
        """5 consecutive policy failures trips the circuit breaker."""
        with patch(
            "gateway.app.enforce._load_and_evaluate_policy",
            side_effect=RuntimeError("DB down"),
        ):
            for _i in range(5):
                result = enforce(
                    db_session,
                    agent_id=test_agent.id,
                    endpoint="/v1/chat",
                    method="POST",
                )
                assert result.decision == Decision.ERROR

        # Breaker should now be OPEN
        assert policy_circuit_breaker.state == CircuitState.OPEN

    def test_open_breaker_denies_all_with_503(self, db_session, test_agent, test_policy):
        """When circuit breaker is OPEN, all requests get 503."""
        # Trip the breaker
        with patch(
            "gateway.app.enforce._load_and_evaluate_policy",
            side_effect=RuntimeError("DB down"),
        ):
            for _ in range(5):
                enforce(
                    db_session,
                    agent_id=test_agent.id,
                    endpoint="/v1/chat",
                    method="POST",
                )

        # Now make a normal request — should be denied by circuit breaker
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        assert result.allowed is False
        assert result.decision == Decision.ERROR
        assert result.deny_reason == DenyReason.CIRCUIT_BREAKER_OPEN
        assert result.status_code == 503

    def test_circuit_breaker_logs_deny(self, db_session, test_agent, test_policy):
        """Circuit breaker denials are logged in the audit trail."""
        # Trip the breaker
        with patch(
            "gateway.app.enforce._load_and_evaluate_policy",
            side_effect=RuntimeError("DB down"),
        ):
            for _ in range(5):
                enforce(
                    db_session,
                    agent_id=test_agent.id,
                    endpoint="/v1/chat",
                    method="POST",
                )

        # Clear audit entries from the errors above
        db_session.query(AuditLog).delete()
        db_session.commit()

        # Make a request while breaker is open
        enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )

        entries = db_session.query(AuditLog).all()
        assert len(entries) == 1
        assert entries[0].decision == "error"
        assert entries[0].request_metadata.get("deny_reason") == "circuit_breaker_open"

    def test_successful_requests_dont_trip_breaker(self, db_session, test_agent, test_policy):
        """Successful policy evaluations don't increment failure count."""
        # Make several successful requests
        for _ in range(10):
            result = enforce(
                db_session,
                agent_id=test_agent.id,
                endpoint="/v1/chat",
                method="POST",
            )
            assert result.allowed is True

        # Breaker should still be CLOSED
        assert policy_circuit_breaker.state == CircuitState.CLOSED


# ── Gateway Endpoints ──────────────────────────────────────────────────


class TestGatewayEndpoints:
    """Verify the gateway REST endpoints."""

    def test_enforce_endpoint_allow(self, client, db_session, test_agent, test_policy):
        """POST /gateway/enforce returns allow for valid agent+policy."""
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "allow"

    def test_enforce_endpoint_deny(self, client, db_session, test_agent):
        """POST /gateway/enforce returns deny for agent without policy."""
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )

        assert resp.status_code == 403
        data = resp.json()
        assert data["decision"] == "deny"
        assert data["deny_reason"] == "no_active_policy"

    def test_circuit_breaker_status_endpoint(self, client):
        """GET /gateway/circuit-breaker returns breaker state."""
        resp = client.get("/gateway/circuit-breaker")

        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "closed"
        assert data["is_accepting_requests"] is True
        assert "config" in data

    def test_health_includes_breaker_state(self, client):
        """GET /health includes circuit breaker state."""
        resp = client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["circuit_breaker"] == "closed"
        assert data["status"] == "ok"
