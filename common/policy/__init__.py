"""Policy evaluation — shared between gateway (enforcement) and API (dry-run).

The evaluator returns a rich ``PolicyDecision`` object so callers can:
  - Gateway: unwrap into ``(allowed, deny_reason)`` for enforcement decisions
    and capture ``when_conditions`` in the audit trail.
  - API: surface the full decision (including which ``when`` condition failed)
    to the policy dry-run endpoint, for onboarding and debugging.

SECURITY: The module is declarative. No ``eval()``, no ``exec()``. All
matching is a finite set of operators on scalar values.
"""

from common.policy.eval import (
    ConditionResult,
    PolicyDecision,
    evaluate_policy,
    evaluate_when,
)

__all__ = [
    "ConditionResult",
    "PolicyDecision",
    "evaluate_policy",
    "evaluate_when",
]
