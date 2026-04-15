"""Policy evaluator — declarative ABAC + endpoint rules.

This module is the single source of policy evaluation semantics, shared between
the gateway's runtime enforcement path and the API's dry-run endpoint.

Rule shape (JSONB):

    {
      "when": { ... optional metadata conditions ... },
      "allowed_endpoints": [...],
      "denied_endpoints": [...],
      "allowed_methods": [...]
    }

The ``when`` clause is optional. If present, ALL conditions must match the
agent's metadata for the policy to apply. If any condition fails, the policy
is treated as absent — which, given the fail-closed default, denies the
request. Missing metadata keys cause conditions to fail.

``when`` condition grammar:

    when:
      environment: "production"                  # equality shorthand
      team:        {in: ["payments", "finance"]} # IN
      framework:   {not_in: ["test-tool"]}       # NOT IN
      # Multiple keys = implicit AND.

SECURITY:
  - Fail-closed default: empty rules, missing policy, or any error → DENY.
  - Declarative only — no eval(), no exec(), no regex, no external calls.
  - Per-condition trace is preserved on the PolicyDecision so auditors can
    see exactly which match failed, with expected vs. actual values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Supported operators on metadata values ──────────────────────────────────

OP_EQ = "eq"
OP_IN = "in"
OP_NOT_IN = "not_in"

SUPPORTED_WHEN_OPERATORS: frozenset[str] = frozenset({OP_EQ, OP_IN, OP_NOT_IN})

# Metadata values we're willing to match against. JSONB permits anything, but
# objects and arrays have no natural equality semantic that buyers would
# reason about. Keep v1 to scalars.
_SCALAR_TYPES = (str, int, float, bool)


# ── Result types ─────────────────────────────────────────────────────────────


@dataclass
class ConditionResult:
    """One entry from a ``when`` clause evaluation.

    Preserved in :class:`PolicyDecision` so audit logs and the dry-run endpoint
    can show which condition failed, with the expected and actual values. This
    is what makes a denial defensible in a compliance review — the audit log
    says not just "denied" but "denied because agent.team == 'sales', expected
    one of ['payments', 'finance']".
    """

    field: str
    op: str  # OP_EQ | OP_IN | OP_NOT_IN
    expected: Any
    actual: Any
    match: bool


@dataclass
class PolicyDecision:
    """Rich evaluation result for a (policy, agent, request) triple.

    The gateway unwraps ``allowed`` + ``deny_reason`` for its enforcement
    contract. The dry-run endpoint surfaces the whole object, including the
    per-condition ``when_conditions`` trace, to the caller.
    """

    allowed: bool
    deny_reason: str | None = None
    """A stable string identifier for the failing rule, formatted as
    ``<category>:<specifics>``. Examples:
    - ``when:team:not_equal:expected=payments,actual=sales``
    - ``allowed_endpoints:not_matched:/v1/admin/users``
    - ``denied_endpoints:/v1/admin/*``
    - ``allowed_methods:not_allowed:DELETE``
    - ``allowed_endpoints:not_configured``
    """

    when_conditions: list[ConditionResult] = field(default_factory=list)
    """Every condition from the ``when`` clause, evaluated in order. Empty
    list means the policy had no ``when`` clause."""

    matched_rule: str | None = None
    """Which rule component authorised the request (on allow) or rejected
    it (on deny). For a deny, equals ``deny_reason``. For an allow, names
    the allowed-endpoint pattern that matched."""


# ── Evaluator ────────────────────────────────────────────────────────────────


def evaluate_when(
    when_clause: dict[str, Any] | None,
    agent_metadata: dict[str, Any],
) -> list[ConditionResult]:
    """Evaluate every condition in a ``when`` clause against agent metadata.

    Returns the per-condition results in declaration order. A condition is
    considered failed if:
      - The referenced metadata key is missing from ``agent_metadata``.
      - The metadata value fails the operator's match test.
      - The condition uses an unsupported operator (validator should catch
        this at policy creation; evaluated here as a failed match so runtime
        stays fail-closed even if a bad policy slips through).

    An empty or missing ``when`` returns an empty list, which callers should
    interpret as "no metadata constraints — policy applies unconditionally".
    """
    if not when_clause:
        return []

    results: list[ConditionResult] = []
    for field_name, condition in when_clause.items():
        op, expected = _decode_condition(condition)
        actual = agent_metadata.get(field_name, _MISSING)
        match = _match(op, expected, actual)
        results.append(
            ConditionResult(
                field=field_name,
                op=op,
                expected=expected,
                # Normalize the sentinel to None so it serializes cleanly over
                # JSON — callers can still detect "missing" because `match`
                # will be False for any missing key that's compared against a
                # real value.
                actual=None if actual is _MISSING else actual,
                match=match,
            )
        )
    return results


def evaluate_policy(
    rules: dict[str, Any],
    agent_metadata: dict[str, Any],
    endpoint: str,
    method: str,
) -> PolicyDecision:
    """Evaluate ``rules`` for an agent against a (endpoint, method) request.

    The ordering matters for audit-trail clarity:
      1. ``when`` clause first — if any condition fails, the entire policy
         is considered inapplicable and the request is denied. The audit log
         captures which condition failed (with expected vs. actual values).
      2. ``denied_endpoints`` — explicit deny list fires next.
      3. ``allowed_endpoints`` — request must match one.
      4. ``allowed_methods`` — method must be permitted.

    Empty or missing ``rules`` denies with ``allowed_endpoints:not_configured``
    — the existing fail-closed behavior. Existing flat policies without a
    ``when`` clause behave identically to the pre-ABAC evaluator.
    """
    # 1. `when` clause
    when_clause = rules.get("when") if isinstance(rules, dict) else None
    when_conditions = evaluate_when(when_clause, agent_metadata)
    for cond in when_conditions:
        if not cond.match:
            # First failing condition wins — cleanest story for the audit log.
            if cond.actual is None and cond.op == OP_EQ:
                reason = f"when:{cond.field}:missing:expected={cond.expected!r}"
            elif cond.op == OP_EQ:
                reason = (
                    f"when:{cond.field}:not_equal:expected={cond.expected!r},actual={cond.actual!r}"
                )
            elif cond.op == OP_IN:
                reason = (
                    f"when:{cond.field}:not_in:expected={cond.expected!r},actual={cond.actual!r}"
                )
            elif cond.op == OP_NOT_IN:
                reason = (
                    f"when:{cond.field}:in_forbidden:"
                    f"expected={cond.expected!r},actual={cond.actual!r}"
                )
            else:
                reason = f"when:{cond.field}:unsupported_op:{cond.op}"
            return PolicyDecision(
                allowed=False,
                deny_reason=reason,
                when_conditions=when_conditions,
                matched_rule=reason,
            )

    # Empty rules beyond a matching `when` still means "no permissions" — DENY.
    if not rules or (len(rules) == 1 and "when" in rules):
        return PolicyDecision(
            allowed=False,
            deny_reason="allowed_endpoints:not_configured",
            when_conditions=when_conditions,
            matched_rule="allowed_endpoints:not_configured",
        )

    # 2. Explicit deny list
    for pattern in rules.get("denied_endpoints", []):
        if _endpoint_matches(endpoint, pattern):
            reason = f"denied_endpoints:{pattern}"
            return PolicyDecision(
                allowed=False,
                deny_reason=reason,
                when_conditions=when_conditions,
                matched_rule=reason,
            )

    # 3. Allowed endpoints
    allowed_endpoints = rules.get("allowed_endpoints", [])
    if not allowed_endpoints:
        return PolicyDecision(
            allowed=False,
            deny_reason="allowed_endpoints:not_configured",
            when_conditions=when_conditions,
            matched_rule="allowed_endpoints:not_configured",
        )

    matched_pattern: str | None = None
    for pattern in allowed_endpoints:
        if _endpoint_matches(endpoint, pattern):
            matched_pattern = pattern
            break
    if matched_pattern is None:
        reason = f"allowed_endpoints:not_matched:{endpoint}"
        return PolicyDecision(
            allowed=False,
            deny_reason=reason,
            when_conditions=when_conditions,
            matched_rule=reason,
        )

    # 4. Allowed methods
    allowed_methods = rules.get("allowed_methods", [])
    if allowed_methods and method.upper() not in {m.upper() for m in allowed_methods}:
        reason = f"allowed_methods:not_allowed:{method}"
        return PolicyDecision(
            allowed=False,
            deny_reason=reason,
            when_conditions=when_conditions,
            matched_rule=reason,
        )

    # All checks passed — ALLOW.
    return PolicyDecision(
        allowed=True,
        deny_reason=None,
        when_conditions=when_conditions,
        matched_rule=f"allowed_endpoints:{matched_pattern}",
    )


# ── Internal helpers ─────────────────────────────────────────────────────────


# Sentinel for "metadata key was absent" — distinguishable from a stored None.
class _Missing:
    def __repr__(self) -> str:
        return "<missing>"


_MISSING = _Missing()


def _decode_condition(condition: Any) -> tuple[str, Any]:
    """Translate a rule DSL condition into ``(op, expected)``.

    - Scalar (str/int/float/bool/None) → implicit equality.
    - Dict with exactly one key in {``in``, ``not_in``} → that operator.
    - Anything else → returned as op=``unsupported`` so the evaluator fails
      closed rather than raising. The validator should catch these at policy
      creation time; this is belt-and-suspenders in case a bad policy slips
      into the DB.
    """
    if isinstance(condition, _SCALAR_TYPES) or condition is None:
        return OP_EQ, condition
    if isinstance(condition, dict) and len(condition) == 1:
        op_key = next(iter(condition))
        if op_key in SUPPORTED_WHEN_OPERATORS:
            return op_key, condition[op_key]
    return "unsupported", condition


def _match(op: str, expected: Any, actual: Any) -> bool:
    """Apply an operator to a value. Returns False for any unknown op."""
    if actual is _MISSING:
        # A missing metadata field never satisfies an equality or IN match,
        # and also never satisfies a NOT IN match (absence is ambiguous, and
        # leaving it to deny keeps us fail-closed).
        return False
    if op == OP_EQ:
        return actual == expected
    if op == OP_IN:
        return isinstance(expected, (list, tuple)) and actual in expected
    if op == OP_NOT_IN:
        return isinstance(expected, (list, tuple)) and actual not in expected
    return False


def _endpoint_matches(endpoint: str, pattern: str) -> bool:
    """Endpoint matching with wildcard support.

    Supports:
      - Exact match: ``/v1/chat`` matches ``/v1/chat``.
      - Prefix wildcard: ``/v1/*`` matches ``/v1/chat`` and ``/v1/embeddings``.
      - Full wildcard: ``*`` matches everything.
    """
    if pattern == "*":
        return True
    if pattern.endswith("/*"):
        prefix = pattern[:-1]  # "/v1/" from "/v1/*"
        return endpoint.startswith(prefix) or endpoint == pattern[:-2]
    return endpoint == pattern
