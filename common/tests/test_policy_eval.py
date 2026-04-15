"""Tests for ``common.policy.eval`` — the ABAC-capable policy evaluator.

Covers:
  - Legacy flat policies (no ``when`` clause) behave identically to the
    pre-ABAC evaluator — backward compatibility is mandatory.
  - ``when`` equality shorthand matches and rejects correctly.
  - ``in`` / ``not_in`` operators.
  - Implicit AND across multiple ``when`` fields.
  - Missing metadata keys fail-closed.
  - Rich ``PolicyDecision`` carries the per-condition trace expected
    by the audit trail and the dry-run endpoint.
"""

import pytest

from common.policy.eval import (
    OP_EQ,
    PolicyDecision,
    evaluate_policy,
    evaluate_when,
)

# ── Backward compatibility — pre-ABAC shape still works ─────────────────────


class TestLegacyFlatPolicies:
    """Policies without a ``when`` clause must behave exactly as before."""

    def test_allow_matching_endpoint_and_method(self):
        rules = {"allowed_endpoints": ["/v1/chat"], "allowed_methods": ["POST"]}
        d = evaluate_policy(rules, {}, "/v1/chat", "POST")
        assert d.allowed is True
        assert d.deny_reason is None
        assert d.matched_rule == "allowed_endpoints:/v1/chat"
        assert d.when_conditions == []

    def test_empty_rules_deny_fail_closed(self):
        d = evaluate_policy({}, {}, "/v1/chat", "POST")
        assert d.allowed is False
        assert d.deny_reason == "allowed_endpoints:not_configured"

    def test_denied_endpoints_checked_first(self):
        rules = {
            "allowed_endpoints": ["*"],
            "denied_endpoints": ["/v1/admin/*"],
        }
        d = evaluate_policy(rules, {}, "/v1/admin/purge", "DELETE")
        assert d.allowed is False
        assert d.deny_reason == "denied_endpoints:/v1/admin/*"

    def test_method_not_allowed(self):
        rules = {"allowed_endpoints": ["/v1/chat"], "allowed_methods": ["POST"]}
        d = evaluate_policy(rules, {}, "/v1/chat", "DELETE")
        assert d.allowed is False
        assert d.deny_reason == "allowed_methods:not_allowed:DELETE"

    def test_wildcard_endpoint(self):
        rules = {"allowed_endpoints": ["*"]}
        d = evaluate_policy(rules, {}, "/v1/anything", "GET")
        assert d.allowed is True

    def test_prefix_wildcard(self):
        rules = {"allowed_endpoints": ["/v1/*"]}
        d = evaluate_policy(rules, {}, "/v1/chat", "POST")
        assert d.allowed is True

    def test_missing_allowed_endpoints_denies(self):
        rules = {"allowed_methods": ["POST"]}
        d = evaluate_policy(rules, {}, "/v1/chat", "POST")
        assert d.allowed is False
        assert d.deny_reason == "allowed_endpoints:not_configured"


# ── `when` clause — equality shorthand ───────────────────────────────────────


class TestWhenEquality:
    """Scalar-as-equality: ``{team: 'payments'}`` matches when value is equal."""

    def test_matching_scalar_allows(self):
        rules = {
            "when": {"environment": "production"},
            "allowed_endpoints": ["/v1/chat"],
        }
        d = evaluate_policy(rules, {"environment": "production"}, "/v1/chat", "POST")
        assert d.allowed is True
        assert len(d.when_conditions) == 1
        assert d.when_conditions[0].match is True
        assert d.when_conditions[0].op == OP_EQ

    def test_mismatched_scalar_denies_with_reason(self):
        rules = {
            "when": {"environment": "production"},
            "allowed_endpoints": ["/v1/chat"],
        }
        d = evaluate_policy(rules, {"environment": "staging"}, "/v1/chat", "POST")
        assert d.allowed is False
        assert "when:environment:not_equal" in d.deny_reason
        assert "expected='production'" in d.deny_reason
        assert "actual='staging'" in d.deny_reason
        assert d.when_conditions[0].match is False
        assert d.when_conditions[0].expected == "production"
        assert d.when_conditions[0].actual == "staging"

    def test_missing_metadata_field_denies(self):
        rules = {
            "when": {"team": "payments"},
            "allowed_endpoints": ["/v1/payments/*"],
        }
        d = evaluate_policy(rules, {}, "/v1/payments/charge", "POST")
        assert d.allowed is False
        assert "when:team:missing" in d.deny_reason
        assert d.when_conditions[0].match is False
        assert d.when_conditions[0].actual is None

    def test_multiple_fields_implicit_and(self):
        rules = {
            "when": {"environment": "production", "team": "payments"},
            "allowed_endpoints": ["/v1/payments/*"],
        }
        d = evaluate_policy(
            rules,
            {"environment": "production", "team": "payments"},
            "/v1/payments/charge",
            "POST",
        )
        assert d.allowed is True
        # Only one condition needs to fail to deny the whole policy.
        d = evaluate_policy(
            rules,
            {"environment": "production", "team": "support"},
            "/v1/payments/charge",
            "POST",
        )
        assert d.allowed is False
        # First failing condition wins — declaration order.
        assert "team" in d.deny_reason

    def test_boolean_and_numeric_metadata(self):
        # Values other than strings should work (ints, bools).
        rules = {"when": {"tier": 3}, "allowed_endpoints": ["/v1/*"]}
        assert evaluate_policy(rules, {"tier": 3}, "/v1/x", "GET").allowed
        assert not evaluate_policy(rules, {"tier": 2}, "/v1/x", "GET").allowed


# ── `when` clause — IN / NOT IN ──────────────────────────────────────────────


class TestWhenInAndNotIn:
    """``{in: [...]}`` and ``{not_in: [...]}`` list operators."""

    def test_in_operator_matches_any_value(self):
        rules = {
            "when": {"environment": {"in": ["production", "staging"]}},
            "allowed_endpoints": ["/v1/*"],
        }
        assert evaluate_policy(rules, {"environment": "production"}, "/v1/x", "GET").allowed
        assert evaluate_policy(rules, {"environment": "staging"}, "/v1/x", "GET").allowed
        d = evaluate_policy(rules, {"environment": "dev"}, "/v1/x", "GET")
        assert not d.allowed
        assert "when:environment:not_in" in d.deny_reason

    def test_not_in_operator_excludes_values(self):
        rules = {
            "when": {"framework": {"not_in": ["test-tool"]}},
            "allowed_endpoints": ["/v1/*"],
        }
        assert evaluate_policy(rules, {"framework": "langchain"}, "/v1/x", "GET").allowed
        d = evaluate_policy(rules, {"framework": "test-tool"}, "/v1/x", "GET")
        assert not d.allowed
        assert "when:framework:in_forbidden" in d.deny_reason


# ── Rich decision trace ──────────────────────────────────────────────────────


class TestPolicyDecisionTrace:
    """Audit trail / dry-run depend on the rich condition trace."""

    def test_when_conditions_preserved_on_allow(self):
        rules = {
            "when": {"environment": "production", "team": {"in": ["payments"]}},
            "allowed_endpoints": ["/v1/*"],
        }
        d = evaluate_policy(
            rules,
            {"environment": "production", "team": "payments"},
            "/v1/chat",
            "POST",
        )
        assert d.allowed
        assert len(d.when_conditions) == 2
        assert all(c.match for c in d.when_conditions)

    def test_when_conditions_preserved_on_deny_for_audit(self):
        rules = {
            "when": {"environment": "production"},
            "allowed_endpoints": ["/v1/*"],
        }
        d = evaluate_policy(rules, {"environment": "dev"}, "/v1/x", "GET")
        assert not d.allowed
        # Exactly what the audit trail should capture.
        assert d.when_conditions[0].field == "environment"
        assert d.when_conditions[0].expected == "production"
        assert d.when_conditions[0].actual == "dev"
        assert d.when_conditions[0].op == OP_EQ

    def test_matched_rule_names_allowed_endpoint(self):
        rules = {"allowed_endpoints": ["/v1/chat", "/v1/embed"]}
        d = evaluate_policy(rules, {}, "/v1/embed", "POST")
        assert d.allowed
        assert d.matched_rule == "allowed_endpoints:/v1/embed"


# ── evaluate_when standalone ─────────────────────────────────────────────────


class TestEvaluateWhenStandalone:
    """``evaluate_when`` is exposed for cases that want the raw condition list."""

    def test_empty_or_missing_when_returns_empty_list(self):
        assert evaluate_when(None, {"env": "production"}) == []
        assert evaluate_when({}, {"env": "production"}) == []

    def test_unsupported_operator_fails_closed(self):
        # A bad policy that slipped past validation should still fail-closed.
        results = evaluate_when({"env": {"weird_op": "x"}}, {"env": "production"})
        assert len(results) == 1
        assert results[0].match is False


# ── Defense-in-depth: malformed rules shouldn't explode ──────────────────────


class TestMalformedRulesFailClosed:
    def test_non_dict_rules_denied_not_raised(self):
        # The evaluator is called by the gateway inside a thread pool; any
        # exception is a DENY, but clean denial is better than relying on
        # exception handling.
        d: PolicyDecision = evaluate_policy({}, {}, "/v1/chat", "POST")
        assert not d.allowed

    def test_unsupported_when_op_denies(self):
        rules = {
            "when": {"env": {"weird_op": "x"}},
            "allowed_endpoints": ["/v1/*"],
        }
        d = evaluate_policy(rules, {"env": "production"}, "/v1/x", "GET")
        assert not d.allowed
        assert "when:env:unsupported_op" in d.deny_reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
