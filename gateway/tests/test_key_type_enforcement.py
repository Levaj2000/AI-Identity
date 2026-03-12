"""Tests for key-type enforcement in the gateway.

Verifies the core security guarantee:
  - Runtime keys (aid_sk_) are DENIED on management endpoints (403)
  - Admin keys (aid_admin_) are DENIED on runtime/proxy endpoints (403)
  - Each key type works on its intended endpoints
  - Legacy keys (no type) are allowed everywhere (backward compat)
  - Key-type enforcement is checked BEFORE circuit breaker and policy
  - Audit log records key-type denials
"""

import uuid

import pytest

from gateway.app.enforce import (
    Decision,
    DenyReason,
    _check_key_type,
    _is_management_endpoint,
    enforce,
    policy_circuit_breaker,
)


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    """Reset the module-level circuit breaker between tests."""
    policy_circuit_breaker.reset()
    yield
    policy_circuit_breaker.reset()


# ── Endpoint Classification Tests ────────────────────────────────────


class TestEndpointClassification:
    """Test that endpoints are correctly classified as management vs runtime."""

    def test_agents_crud_is_management(self):
        assert _is_management_endpoint("/api/v1/agents")
        assert _is_management_endpoint("/api/v1/agents/123")
        assert _is_management_endpoint("/api/v1/agents/123/keys")
        assert _is_management_endpoint("/api/v1/agents/123/keys/456")
        assert _is_management_endpoint("/api/v1/agents/123/keys/rotate")

    def test_policy_endpoints_are_management(self):
        assert _is_management_endpoint("/api/v1/policies")
        assert _is_management_endpoint("/api/v1/policies/123")

    def test_audit_endpoints_are_management(self):
        assert _is_management_endpoint("/api/v1/audit")
        assert _is_management_endpoint("/api/v1/audit/verify")

    def test_user_endpoints_are_management(self):
        assert _is_management_endpoint("/api/v1/users")
        assert _is_management_endpoint("/api/v1/users/123")

    def test_proxy_endpoints_are_not_management(self):
        assert not _is_management_endpoint("/v1/chat")
        assert not _is_management_endpoint("/v1/embeddings")
        assert not _is_management_endpoint("/v1/completions")

    def test_gateway_endpoints_are_not_management(self):
        assert not _is_management_endpoint("/gateway/enforce")
        assert not _is_management_endpoint("/gateway/circuit-breaker")

    def test_health_is_not_management(self):
        assert not _is_management_endpoint("/health")
        assert not _is_management_endpoint("/")

    def test_wildcard_proxy_is_not_management(self):
        assert not _is_management_endpoint("/v1/any/path/here")


# ── Key-Type Check Function Tests ────────────────────────────────────


class TestCheckKeyType:
    """Test the _check_key_type function directly."""

    def test_runtime_key_allowed_on_proxy(self):
        result = _check_key_type("runtime", "/v1/chat")
        assert result is None  # None = allowed

    def test_runtime_key_denied_on_management(self):
        result = _check_key_type("runtime", "/api/v1/agents")
        assert result is not None
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.RUNTIME_KEY_ON_MANAGEMENT
        assert result.status_code == 403

    def test_admin_key_allowed_on_management(self):
        result = _check_key_type("admin", "/api/v1/agents")
        assert result is None  # None = allowed

    def test_admin_key_denied_on_proxy(self):
        result = _check_key_type("admin", "/v1/chat")
        assert result is not None
        assert result.decision == Decision.DENY
        assert result.deny_reason == DenyReason.ADMIN_KEY_ON_RUNTIME
        assert result.status_code == 403

    def test_no_key_type_allowed_everywhere(self):
        """Legacy keys with no type are allowed on all endpoints."""
        assert _check_key_type(None, "/v1/chat") is None
        assert _check_key_type(None, "/api/v1/agents") is None
        assert _check_key_type(None, "/api/v1/agents/123/keys") is None

    def test_runtime_key_on_key_management(self):
        """Runtime key cannot manage keys — that's a management endpoint."""
        result = _check_key_type("runtime", "/api/v1/agents/123/keys")
        assert result is not None
        assert result.deny_reason == DenyReason.RUNTIME_KEY_ON_MANAGEMENT

    def test_admin_key_on_gateway_proxy(self):
        """Admin key cannot use gateway proxy."""
        result = _check_key_type("admin", "/gateway/enforce")
        assert result is not None
        assert result.deny_reason == DenyReason.ADMIN_KEY_ON_RUNTIME


# ── Full Enforcement Flow Tests ──────────────────────────────────────


class TestEnforceKeyTypeSeparation:
    """Test key-type enforcement through the full enforce() flow."""

    def test_runtime_key_denied_on_management_endpoint(
        self, db_session, test_agent, test_policy
    ):
        """CRITICAL: Runtime key returns 403 on management endpoints."""
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/api/v1/agents",
            method="GET",
            key_type="runtime",
        )
        assert not result.allowed
        assert result.status_code == 403
        assert result.deny_reason == DenyReason.RUNTIME_KEY_ON_MANAGEMENT

    def test_admin_key_denied_on_proxy_endpoint(
        self, db_session, test_agent, test_policy
    ):
        """CRITICAL: Admin key returns 403 on proxy endpoints."""
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
            key_type="admin",
        )
        assert not result.allowed
        assert result.status_code == 403
        assert result.deny_reason == DenyReason.ADMIN_KEY_ON_RUNTIME

    def test_runtime_key_allowed_on_proxy(
        self, db_session, test_agent, test_policy
    ):
        """Runtime key succeeds on proxy endpoints (when policy allows)."""
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
            key_type="runtime",
        )
        assert result.allowed
        assert result.status_code == 200

    def test_admin_key_allowed_on_management(
        self, db_session, test_agent, test_policy
    ):
        """Admin key proceeds to policy check on management endpoints.

        Note: May still be denied by policy if the policy doesn't cover
        management endpoints. This test verifies the key-type gate passes.
        """
        # The test_policy allows /v1/*, not /api/v1/agents — so policy will deny.
        # But the key-type check should pass (not 403 for key-type mismatch).
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/api/v1/agents",
            method="GET",
            key_type="admin",
        )
        # Key-type check passes, but policy denies (no rule for /api/v1/agents)
        assert result.deny_reason != DenyReason.ADMIN_KEY_ON_RUNTIME
        # It should be denied by policy, not by key type
        assert result.deny_reason == DenyReason.POLICY_DENIED

    def test_no_key_type_still_works(
        self, db_session, test_agent, test_policy
    ):
        """Backward compat: no key_type = legacy behavior, no key-type gate."""
        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
            key_type=None,
        )
        assert result.allowed


# ── Key-Type Checked Before Other Enforcement ────────────────────────


class TestKeyTypeCheckOrder:
    """Verify key-type is checked FIRST, before circuit breaker and agent lookup."""

    def test_key_type_denied_before_agent_validation(self, db_session):
        """Key-type denial happens even if agent_id is non-existent."""
        fake_agent_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
        result = enforce(
            db_session,
            agent_id=fake_agent_id,
            endpoint="/api/v1/agents",
            method="GET",
            key_type="runtime",
        )
        # Should be key-type denial, NOT agent-not-found
        assert result.deny_reason == DenyReason.RUNTIME_KEY_ON_MANAGEMENT
        assert result.status_code == 403

    def test_key_type_denied_before_circuit_breaker(self, db_session):
        """Key-type denial happens even if circuit breaker is open."""
        # Trip the circuit breaker
        for _i in range(10):
            policy_circuit_breaker.record_failure()

        fake_agent_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
        result = enforce(
            db_session,
            agent_id=fake_agent_id,
            endpoint="/v1/chat",
            method="POST",
            key_type="admin",
        )
        # Should be key-type denial, NOT circuit breaker
        assert result.deny_reason == DenyReason.ADMIN_KEY_ON_RUNTIME
        assert result.status_code == 403


# ── Audit Logging for Key-Type Denials ───────────────────────────────


class TestKeyTypeDenialAudit:
    """Test that key-type denials are recorded in the audit log."""

    def test_runtime_key_denial_creates_audit_entry(
        self, db_session, test_agent
    ):
        """Key-type denial should write an audit log entry."""
        from common.models import AuditLog

        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/api/v1/agents",
            method="GET",
            key_type="runtime",
        )
        assert not result.allowed

        # Check audit log
        entry = (
            db_session.query(AuditLog)
            .filter(AuditLog.agent_id == test_agent.id)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert entry is not None
        assert entry.decision == "deny"
        assert entry.endpoint == "/api/v1/agents"
        assert entry.request_metadata.get("deny_reason") == "runtime_key_on_management_endpoint"
        assert entry.request_metadata.get("key_type") == "runtime"

    def test_admin_key_denial_creates_audit_entry(
        self, db_session, test_agent
    ):
        """Admin key-type denial should write an audit log entry."""
        from common.models import AuditLog

        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
            key_type="admin",
        )
        assert not result.allowed

        entry = (
            db_session.query(AuditLog)
            .filter(AuditLog.agent_id == test_agent.id)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert entry is not None
        assert entry.decision == "deny"
        assert entry.request_metadata.get("deny_reason") == "admin_key_on_runtime_endpoint"
        assert entry.request_metadata.get("key_type") == "admin"


# ── Gateway HTTP Endpoint Tests ──────────────────────────────────────


class TestGatewayEnforceEndpointKeyType:
    """Test the POST /gateway/enforce endpoint with key_type param."""

    def test_runtime_key_denied_on_management_via_http(
        self, client, test_agent, test_policy
    ):
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/api/v1/agents",
                "method": "GET",
                "key_type": "runtime",
            },
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["deny_reason"] == "runtime_key_on_management_endpoint"

    def test_admin_key_denied_on_proxy_via_http(
        self, client, test_agent, test_policy
    ):
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
                "key_type": "admin",
            },
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["deny_reason"] == "admin_key_on_runtime_endpoint"

    def test_runtime_key_allowed_on_proxy_via_http(
        self, client, test_agent, test_policy
    ):
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
                "key_type": "runtime",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "allow"

    def test_no_key_type_still_works_via_http(
        self, client, test_agent, test_policy
    ):
        """No key_type param = legacy behavior."""
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

    def test_invalid_key_type_rejected(self, client, test_agent, test_policy):
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
                "key_type": "superadmin",
            },
        )
        assert resp.status_code == 422
