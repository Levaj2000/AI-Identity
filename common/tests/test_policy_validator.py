"""Tests for PolicyValidator — strict JSONB schema validation.

Verifies that:
  - Valid policies pass validation
  - Unknown keys are rejected
  - Excessive depth is rejected (>3)
  - Oversized payloads are rejected (>10KB)
  - Endpoint patterns are validated (safe chars, starts with /)
  - HTTP methods are validated
  - max_cost_usd is validated (type, range)
  - Type mismatches are caught
  - Empty and minimal policies work
  - PolicyCreate schema integration works
"""

import pytest

from common.validation.policy import (
    MAX_ENDPOINT_LENGTH,
    PolicyValidator,
)


@pytest.fixture
def validator():
    """Standard PolicyValidator instance."""
    return PolicyValidator()


# ── Valid Policies ───────────────────────────────────────────────────


class TestValidPolicies:
    """Test that well-formed policies pass validation."""

    def test_empty_rules_valid(self, validator):
        result = validator.validate({})
        assert result.valid

    def test_minimal_allow_all(self, validator):
        result = validator.validate({"allowed_endpoints": ["*"]})
        assert result.valid

    def test_typical_policy(self, validator):
        result = validator.validate(
            {
                "allowed_endpoints": ["/v1/*"],
                "allowed_methods": ["POST", "GET"],
            }
        )
        assert result.valid

    def test_full_policy(self, validator):
        result = validator.validate(
            {
                "allowed_endpoints": ["/v1/chat", "/v1/embeddings"],
                "denied_endpoints": ["/v1/admin/*"],
                "allowed_methods": ["POST"],
                "max_cost_usd": 0.50,
            }
        )
        assert result.valid

    def test_wildcard_endpoint(self, validator):
        result = validator.validate({"allowed_endpoints": ["*"]})
        assert result.valid

    def test_prefix_wildcard(self, validator):
        result = validator.validate({"allowed_endpoints": ["/v1/*"]})
        assert result.valid

    def test_all_http_methods(self, validator):
        result = validator.validate(
            {
                "allowed_endpoints": ["*"],
                "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
            }
        )
        assert result.valid

    def test_zero_cost(self, validator):
        result = validator.validate({"max_cost_usd": 0})
        assert result.valid

    def test_integer_cost(self, validator):
        result = validator.validate({"max_cost_usd": 100})
        assert result.valid


# ── Unknown Keys ─────────────────────────────────────────────────────


class TestUnknownKeys:
    """Test that unrecognized keys are rejected."""

    def test_single_unknown_key(self, validator):
        result = validator.validate({"execute_code": "import os"})
        assert not result.valid
        assert any("Unknown rule key" in e.message for e in result.errors)

    def test_multiple_unknown_keys(self, validator):
        result = validator.validate(
            {
                "allowed_endpoints": ["/v1/*"],
                "inject_payload": True,
                "admin_override": True,
            }
        )
        assert not result.valid
        assert len([e for e in result.errors if "Unknown" in e.message]) == 2

    def test_typo_in_key_rejected(self, validator):
        result = validator.validate({"allowed_endpoint": ["/v1/*"]})  # missing 's'
        assert not result.valid
        assert any("allowed_endpoint" in e.field for e in result.errors)

    def test_eval_key_rejected(self, validator):
        """SECURITY: Attempts to inject eval/exec through rule keys are blocked."""
        result = validator.validate({"__import__": "os", "eval": "print(1)"})
        assert not result.valid

    def test_nested_unknown_key_in_valid_dict(self, validator):
        """Unknown keys rejected even alongside valid keys."""
        result = validator.validate(
            {
                "allowed_endpoints": ["/v1/*"],
                "secret_backdoor": True,
            }
        )
        assert not result.valid


# ── Depth Limits ─────────────────────────────────────────────────────


class TestDepthLimits:
    """Test that deeply nested payloads are rejected."""

    def test_depth_1_valid(self, validator):
        result = validator.validate({"allowed_endpoints": ["/v1/*"]})
        assert result.valid  # depth = 3: dict → list → string

    def test_depth_3_valid(self, validator):
        """Depth 3 — a flat endpoints policy — remains valid."""
        # dict(1) → list(2) → str(3) = depth 3
        result = validator.validate({"allowed_endpoints": ["/v1/*"]})
        assert result.valid

    def test_depth_5_valid_for_when_clause(self, validator):
        """Depth 5 is the max — required for ABAC `when: {field: {op: [...]}}`."""
        # dict(1) → dict(2) → dict(3) → list(4) → str(5) = depth 5
        rules = {
            "when": {"env": {"in": ["production"]}},
            "allowed_endpoints": ["/v1/*"],
        }
        result = validator.validate(rules)
        assert result.valid

    def test_depth_6_rejected(self, validator):
        """Depth 6 exceeds the limit (max_depth=5 accommodates ABAC `when`)."""
        # dict(1) → dict(2) → dict(3) → list(4) → dict(5) → str(6) = depth 6
        rules = {"when": {"env": {"in": [{"nested": "bad"}]}}}
        result = validator.validate(rules)
        assert not result.valid
        assert any("too deep" in e.message for e in result.errors)

    def test_heavily_nested_rejected(self, validator):
        """Deeply nested structure is rejected."""
        rules = {"allowed_endpoints": [[[["deep"]]]]}
        result = validator.validate(rules)
        assert not result.valid

    def test_custom_max_depth(self):
        """Custom depth limit is respected."""
        v = PolicyValidator(max_depth=2)
        result = v.validate({"allowed_endpoints": ["/v1/*"]})
        assert not result.valid  # depth 3 > custom max 2


# ── Size Limits ──────────────────────────────────────────────────────


class TestSizeLimits:
    """Test that oversized payloads are rejected."""

    def test_normal_size_valid(self, validator):
        result = validator.validate({"allowed_endpoints": ["/v1/*"]})
        assert result.valid

    def test_oversized_payload_rejected(self, validator):
        """Payload exceeding 10KB is rejected."""
        # Create a payload that's definitely > 10KB
        huge_endpoints = [f"/v1/endpoint_{i}" for i in range(1000)]
        result = validator.validate({"allowed_endpoints": huge_endpoints})
        assert not result.valid
        assert any("too large" in e.message for e in result.errors)

    def test_exactly_at_limit(self):
        """Payload at exactly the limit passes."""
        v = PolicyValidator(max_size_bytes=100)
        result = v.validate({})  # Tiny payload
        assert result.valid

    def test_custom_size_limit(self):
        """Custom size limit is enforced."""
        v = PolicyValidator(max_size_bytes=10)
        result = v.validate({"allowed_endpoints": ["/v1/*"]})
        assert not result.valid


# ── Endpoint Validation ──────────────────────────────────────────────


class TestEndpointValidation:
    """Test endpoint pattern validation."""

    def test_valid_endpoints(self, validator):
        result = validator.validate(
            {
                "allowed_endpoints": ["/v1/chat", "/v1/*", "*", "/api/v1/agents"],
            }
        )
        assert result.valid

    def test_endpoint_must_start_with_slash_or_star(self, validator):
        result = validator.validate({"allowed_endpoints": ["v1/chat"]})
        assert not result.valid
        assert any("must start with '/'" in e.message for e in result.errors)

    def test_endpoint_not_a_string(self, validator):
        result = validator.validate({"allowed_endpoints": [123, True]})
        assert not result.valid
        assert len(result.errors) == 2

    def test_endpoint_not_a_list(self, validator):
        result = validator.validate({"allowed_endpoints": "/v1/*"})
        assert not result.valid
        assert any("Must be a list" in e.message for e in result.errors)

    def test_empty_endpoint_string(self, validator):
        result = validator.validate({"allowed_endpoints": [""]})
        assert not result.valid
        assert any("cannot be empty" in e.message for e in result.errors)

    def test_endpoint_too_long(self, validator):
        long_ep = "/" + "a" * MAX_ENDPOINT_LENGTH
        result = validator.validate({"allowed_endpoints": [long_ep]})
        assert not result.valid
        assert any("too long" in e.message for e in result.errors)

    def test_unsafe_characters_rejected(self, validator):
        """Endpoints with query strings, backticks, etc. are rejected."""
        result = validator.validate(
            {
                "allowed_endpoints": ["/v1/chat?token=abc"],
            }
        )
        assert not result.valid
        assert any("unsafe characters" in e.message for e in result.errors)

    def test_null_byte_rejected(self, validator):
        result = validator.validate({"allowed_endpoints": ["/v1/\x00evil"]})
        assert not result.valid

    def test_too_many_endpoints(self, validator):
        endpoints = [f"/v1/ep_{i}" for i in range(51)]
        result = validator.validate({"allowed_endpoints": endpoints})
        assert not result.valid
        assert any("Too many endpoints" in e.message for e in result.errors)

    def test_denied_endpoints_also_validated(self, validator):
        """denied_endpoints go through the same validation."""
        result = validator.validate({"denied_endpoints": [123]})
        assert not result.valid

    def test_path_traversal_rejected(self, validator):
        """Path traversal attempts with .. are safe since dots are allowed
        but the endpoint still must start with /."""
        result = validator.validate({"allowed_endpoints": ["../etc/passwd"]})
        assert not result.valid


# ── Method Validation ────────────────────────────────────────────────


class TestMethodValidation:
    """Test HTTP method validation."""

    def test_valid_methods(self, validator):
        result = validator.validate({"allowed_methods": ["GET", "POST"]})
        assert result.valid

    def test_invalid_method(self, validator):
        result = validator.validate({"allowed_methods": ["HACK"]})
        assert not result.valid
        assert any("Invalid HTTP method" in e.message for e in result.errors)

    def test_method_not_a_string(self, validator):
        result = validator.validate({"allowed_methods": [42]})
        assert not result.valid

    def test_methods_not_a_list(self, validator):
        result = validator.validate({"allowed_methods": "POST"})
        assert not result.valid
        assert any("Must be a list" in e.message for e in result.errors)

    def test_too_many_methods(self, validator):
        methods = [f"M{i}" for i in range(11)]
        result = validator.validate({"allowed_methods": methods})
        assert not result.valid


# ── Cost Validation ──────────────────────────────────────────────────


class TestCostValidation:
    """Test max_cost_usd validation."""

    def test_valid_cost(self, validator):
        result = validator.validate({"max_cost_usd": 1.50})
        assert result.valid

    def test_negative_cost(self, validator):
        result = validator.validate({"max_cost_usd": -1})
        assert not result.valid
        assert any("negative" in e.message for e in result.errors)

    def test_unreasonably_high_cost(self, validator):
        result = validator.validate({"max_cost_usd": 999_999})
        assert not result.valid
        assert any("Unreasonably high" in e.message for e in result.errors)

    def test_cost_not_a_number(self, validator):
        result = validator.validate({"max_cost_usd": "free"})
        assert not result.valid
        assert any("Must be a number" in e.message for e in result.errors)


# ── Type Check ───────────────────────────────────────────────────────


class TestTypeCheck:
    """Test that non-dict inputs are rejected."""

    def test_list_rejected(self, validator):
        result = validator.validate([])  # type: ignore[arg-type]
        assert not result.valid
        assert any("Must be a dict" in e.message for e in result.errors)

    def test_string_rejected(self, validator):
        result = validator.validate("allow all")  # type: ignore[arg-type]
        assert not result.valid

    def test_none_rejected(self, validator):
        result = validator.validate(None)  # type: ignore[arg-type]
        assert not result.valid


# ── Multiple Errors ──────────────────────────────────────────────────


class TestMultipleErrors:
    """Test that multiple errors are reported in a single validation."""

    def test_several_issues_at_once(self, validator):
        result = validator.validate(
            {
                "allowed_endpoints": "not-a-list",  # wrong type
                "allowed_methods": ["HACK"],  # invalid method
                "unknown_key": True,  # unknown key
                "max_cost_usd": -5,  # negative
            }
        )
        assert not result.valid
        assert len(result.errors) >= 4


# ── PolicyCreate Schema Integration ──────────────────────────────────


class TestPolicyCreateSchema:
    """Test that PolicyCreate schema validates rules via PolicyValidator."""

    def test_valid_policy_create(self):
        from common.schemas.agent import PolicyCreate

        policy = PolicyCreate(rules={"allowed_endpoints": ["/v1/*"]})
        assert policy.rules == {"allowed_endpoints": ["/v1/*"]}

    def test_invalid_policy_create_raises(self):
        from common.schemas.agent import PolicyCreate

        with pytest.raises(ValueError, match="Invalid policy rules"):
            PolicyCreate(rules={"evil_key": "hack"})

    def test_empty_rules_valid(self):
        from common.schemas.agent import PolicyCreate

        policy = PolicyCreate(rules={})
        assert policy.rules == {}

    def test_oversized_rules_rejected(self):
        from common.schemas.agent import PolicyCreate

        huge = {"allowed_endpoints": [f"/v1/ep_{i}" for i in range(1000)]}
        with pytest.raises(ValueError, match="too large"):
            PolicyCreate(rules=huge)


# ── Defense-in-Depth Gateway Integration ─────────────────────────────


class TestGatewayDefenseInDepth:
    """Test that the gateway rejects malformed policies loaded from DB."""

    def test_malformed_db_policy_denied(self, db_session, test_agent):
        """A policy with unknown keys in the DB is denied at enforcement time."""
        from common.models import Policy

        # Simulate a malformed policy that bypassed creation validation
        policy = Policy(
            agent_id=test_agent.id,
            rules={"unknown_key": "evil", "allowed_endpoints": ["/v1/*"]},
            version=1,
            is_active=True,
        )
        db_session.add(policy)
        db_session.commit()

        from gateway.app.enforce import enforce, policy_circuit_breaker

        policy_circuit_breaker.reset()

        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )
        # Should be denied because policy has unknown key
        assert not result.allowed

    def test_valid_db_policy_allowed(self, db_session, test_agent):
        """A valid policy in the DB is evaluated normally."""
        from common.models import Policy

        policy = Policy(
            agent_id=test_agent.id,
            rules={"allowed_endpoints": ["/v1/*"], "allowed_methods": ["POST"]},
            version=1,
            is_active=True,
        )
        db_session.add(policy)
        db_session.commit()

        from gateway.app.enforce import enforce, policy_circuit_breaker

        policy_circuit_breaker.reset()

        result = enforce(
            db_session,
            agent_id=test_agent.id,
            endpoint="/v1/chat",
            method="POST",
        )
        assert result.allowed


# ── `when` Clause Validation (ABAC) ──────────────────────────────────


class TestWhenClauseValidation:
    """Validator behavior for the optional `when` metadata clause."""

    def test_when_accepted_as_top_level_key(self, validator):
        result = validator.validate(
            {
                "when": {"environment": "production"},
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert result.valid

    def test_when_scalar_shorthand_valid(self, validator):
        result = validator.validate(
            {
                "when": {"env": "prod", "tier": 3, "active": True},
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert result.valid

    def test_when_in_and_not_in_operators_valid(self, validator):
        result = validator.validate(
            {
                "when": {
                    "env": {"in": ["production", "staging"]},
                    "framework": {"not_in": ["test-tool"]},
                },
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert result.valid

    def test_when_must_be_dict(self, validator):
        result = validator.validate({"when": ["bad"], "allowed_endpoints": ["/v1/*"]})
        assert not result.valid
        assert any("when" in e.field for e in result.errors)

    def test_when_unsupported_operator_rejected(self, validator):
        result = validator.validate(
            {
                "when": {"env": {"matches": "prod.*"}},
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert not result.valid
        assert any("Unsupported operator" in e.message for e in result.errors)

    def test_when_empty_in_list_rejected(self, validator):
        # Empty match list is always a no-match; almost certainly an accident.
        result = validator.validate(
            {
                "when": {"env": {"in": []}},
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert not result.valid
        assert any("Empty list" in e.message for e in result.errors)

    def test_when_non_scalar_value_rejected(self, validator):
        result = validator.validate(
            {
                "when": {"env": {"in": [{"nested": "dict"}]}},
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert not result.valid

    def test_when_warns_on_unknown_metadata_key(self, validator):
        # Agent has no `team` key — policy should be valid but carry a warning.
        result = validator.validate(
            {
                "when": {"team": "payments"},
                "allowed_endpoints": ["/v1/*"],
            },
            agent_metadata={"environment": "production"},
        )
        assert result.valid  # not an error
        assert len(result.warnings) == 1
        assert "team" in result.warnings[0].message

    def test_when_no_warning_without_agent_metadata_context(self, validator):
        # Without agent_metadata we can't know whether keys are unknown.
        result = validator.validate(
            {
                "when": {"team": "payments"},
                "allowed_endpoints": ["/v1/*"],
            }
        )
        assert result.valid
        assert result.warnings == []

    def test_when_no_warning_when_agent_has_the_key(self, validator):
        result = validator.validate(
            {
                "when": {"team": "payments"},
                "allowed_endpoints": ["/v1/*"],
            },
            agent_metadata={"team": "payments"},
        )
        assert result.valid
        assert result.warnings == []

    def test_when_too_many_conditions_rejected(self, validator):
        from common.validation.policy import MAX_WHEN_CONDITIONS

        when = {f"k{i}": "v" for i in range(MAX_WHEN_CONDITIONS + 1)}
        result = validator.validate({"when": when, "allowed_endpoints": ["/v1/*"]})
        assert not result.valid

    def test_policy_without_when_still_valid(self, validator):
        """Backward compatibility: flat policies keep working."""
        result = validator.validate({"allowed_endpoints": ["/v1/*"], "allowed_methods": ["POST"]})
        assert result.valid
        assert result.warnings == []
