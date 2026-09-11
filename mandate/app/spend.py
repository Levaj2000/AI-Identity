"""Spend-limit evaluation for mandates — pure logic, no I/O.

The route in routers/mandates.py owns persistence (MongoDB state, the
mandate_events log, the hash-chained audit entry); this module owns the
decision so it can be tested without a database.

Two evaluation modes (see RecordSpendRequest):
  enforce    — the default. A spend that would cross the limit is DENIED
               and not recorded; the mandate stays active with its
               remaining budget intact. (Prevention.)
  settlement — the money already moved (payment-processor webhook,
               out-of-band channel). The spend is recorded even when it
               crosses the limit, and a crossing flips the mandate to
               `exceeded` — a terminal state like revoked. (Detection.)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from common.policy.eval import evaluate_when
from mandate.app.schemas import MandateStatus, SpendLimit

# deny_reason vocabulary — flat strings, allowlisted in the audit sanitizer
DENY_MANDATE_INACTIVE = "mandate_inactive"
DENY_CURRENCY_MISMATCH = "currency_mismatch"
DENY_LIMIT_EXCEEDED = "spend_limit_exceeded"
DENY_CONDITIONS_UNMET = "mandate_conditions_unmet"


@dataclass(frozen=True)
class SpendOutcome:
    """Result of evaluating one spend against a mandate's current state."""

    accepted: bool  # spend gets recorded (spent_cents increments)
    exceeded: bool  # this spend crossed the limit (settlement path only)
    audit_decision: str  # "allow" | "deny" — what the chained audit entry says
    new_spent_cents: int  # cumulative spend after this call
    new_status: MandateStatus  # status after this call (may be unchanged)
    deny_reason: str | None = None
    # Which conditions were checked and how they landed. Empty when the
    # mandate carries none. Flat dicts so the caller can put them straight
    # into the audit row without another mapping step.
    condition_results: list[dict[str, Any]] = field(default_factory=list)


def evaluate_spend(
    *,
    status: MandateStatus,
    spend_limit: SpendLimit | None,
    spent_cents: int,
    amount_cents: int,
    currency: str,
    settlement: bool,
    conditions: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> SpendOutcome:
    """Evaluate one spend attempt. Pure — no side effects.

    Every deny is a first-class outcome (recorded to the audit chain by the
    caller), never a silent drop: denials are the highest-value events in
    the trail.

    `conditions` is the mandate's signed ABAC clause and `context` is what
    the enforcement point knows about this request (agent metadata plus the
    endpoint and method). They are evaluated by `common.policy.eval`, the
    same function that evaluates a policy's `when` clause, so a mandate
    condition and a policy condition mean the same thing and fail the same
    way: a missing key or an unknown operator is a failed match, never a
    pass.

    Checked before the limit, because a condition that does not hold means
    the grant does not cover this request at all, and there is no point
    asking how much of a budget a non-applicable grant has left.
    """
    if status != MandateStatus.active:
        return SpendOutcome(
            accepted=False,
            exceeded=False,
            audit_decision="deny",
            new_spent_cents=spent_cents,
            new_status=status,
            deny_reason=DENY_MANDATE_INACTIVE,
        )

    # Conditions. `evaluate_when` returns one result per condition in
    # declaration order and an empty list when there is nothing to check.
    results = [asdict(r) for r in evaluate_when(conditions, context or {})]
    if results and not all(r["match"] for r in results):
        return SpendOutcome(
            accepted=False,
            exceeded=False,
            audit_decision="deny",
            new_spent_cents=spent_cents,
            new_status=status,
            deny_reason=DENY_CONDITIONS_UNMET,
            condition_results=results,
        )

    if spend_limit is not None and spend_limit.currency != currency:
        return SpendOutcome(
            accepted=False,
            exceeded=False,
            audit_decision="deny",
            new_spent_cents=spent_cents,
            new_status=status,
            deny_reason=DENY_CURRENCY_MISMATCH,
            condition_results=results,
        )

    new_total = spent_cents + amount_cents

    # No monetary authority on the mandate → spends are tracked, not limited.
    if spend_limit is None or new_total <= spend_limit.limit_cents:
        return SpendOutcome(
            accepted=True,
            exceeded=False,
            audit_decision="allow",
            new_spent_cents=new_total,
            new_status=status,
            condition_results=results,
        )

    # Crossing the limit.
    if settlement:
        # Money already moved — record the fact, flip the mandate. The
        # audit decision is still "deny": the mandate check failed even
        # though the funds moved out-of-band; that IS the breach record.
        return SpendOutcome(
            accepted=True,
            exceeded=True,
            audit_decision="deny",
            new_spent_cents=new_total,
            new_status=MandateStatus.exceeded,
            deny_reason=DENY_LIMIT_EXCEEDED,
            condition_results=results,
        )

    # Enforcement path — reject, don't record, budget intact.
    return SpendOutcome(
        accepted=False,
        exceeded=False,
        audit_decision="deny",
        new_spent_cents=spent_cents,
        new_status=status,
        deny_reason=DENY_LIMIT_EXCEEDED,
        condition_results=results,
    )
