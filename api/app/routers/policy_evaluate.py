"""Policy dry-run endpoint.

``POST /api/v1/policy/evaluate`` takes either a real agent or a hypothetical
(``agent_metadata``, ``rules``) pair and returns the full :class:`PolicyDecision`
without executing the request. This is the "why was this denied?" inspection
tool for policy authors and the trust-signal endpoint enterprise buyers can
use during onboarding to test ``when`` conditions before going live.

Nothing is persisted; nothing is enforced. The endpoint is read-only.

AuthZ:
  - Authenticated users only (standard ``get_current_user`` dependency).
  - If ``agent_id`` is supplied, the caller must own the agent (or share its
    organization) — enforced via :func:`common.queries.get_user_agent`.
  - ``rules`` / ``agent_metadata`` (what-if) mode requires no agent
    ownership — any authenticated user can simulate a policy against
    arbitrary metadata.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import Policy, User, get_db
from common.policy import evaluate_policy
from common.queries import get_user_agent
from common.schemas.policy_eval import (
    ConditionResultResponse,
    PolicyEvaluateRequest,
    PolicyEvaluateResponse,
)
from common.validation.policy import PolicyValidator

logger = logging.getLogger("ai_identity.api.policy_evaluate")

router = APIRouter(prefix="/api/v1/policy", tags=["policies"])


@router.post(
    "/evaluate",
    response_model=PolicyEvaluateResponse,
    summary="Dry-run policy evaluation",
    response_description=(
        "The full PolicyDecision — decision, matched/failing rule, and "
        "per-condition `when` trace — without enforcing the request."
    ),
)
def evaluate_policy_dryrun(
    body: PolicyEvaluateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate a policy against a request without enforcing it.

    Two modes:

    1. **Agent-bound** — supply ``agent_id``. Uses the agent's active policy
       and current metadata. Useful for "why did this agent get denied?"
       debugging.

    2. **What-if** — supply ``rules`` and optionally ``agent_metadata``. No
       real agent referenced. Useful for policy authoring — editors can test
       ``when`` conditions against hypothetical metadata before committing
       the policy.

    The response mirrors the runtime evaluator's ``PolicyDecision`` so a
    dashboard can render "this would have been denied because team=='sales',
    expected one of ['payments', 'finance']" from a single call.
    """
    # ── Mode 1: agent-bound evaluation ──
    if body.agent_id is not None:
        agent = get_user_agent(db, user, body.agent_id)
        policy = (
            db.query(Policy)
            .filter(Policy.agent_id == agent.id, Policy.is_active.is_(True))
            .order_by(Policy.version.desc())
            .first()
        )
        if policy is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Agent has no active policy. Create one at "
                    "POST /api/v1/agents/{agent_id}/policies first."
                ),
            )

        # Defense-in-depth: invalid rules in the DB are treated the same way
        # the runtime treats them — evaluation denied, surfaced to the caller
        # with a useful error.
        validation = PolicyValidator().validate(policy.rules)
        if not validation.valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Active policy rules failed validation; "
                    "the runtime treats this as DENY.",
                    "errors": [{"field": e.field, "message": e.message} for e in validation.errors],
                },
            )

        rules = policy.rules
        agent_metadata = dict(agent.metadata_ or {})
        policy_id: int | None = policy.id
    # ── Mode 2: what-if evaluation ──
    else:
        assert body.rules is not None  # model validator enforces this
        # Validate the supplied rules like we would at policy creation time.
        validation = PolicyValidator().validate(body.rules)
        if not validation.valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Rules failed validation.",
                    "errors": [{"field": e.field, "message": e.message} for e in validation.errors],
                },
            )
        rules = body.rules
        agent_metadata = dict(body.agent_metadata or {})
        policy_id = None

    decision = evaluate_policy(rules, agent_metadata, body.endpoint, body.method)

    logger.info(
        "Dry-run: user=%s mode=%s allowed=%s reason=%s",
        user.id,
        "agent" if body.agent_id else "what-if",
        decision.allowed,
        decision.deny_reason,
    )

    return PolicyEvaluateResponse(
        allowed=decision.allowed,
        deny_reason=decision.deny_reason,
        matched_rule=decision.matched_rule,
        when_conditions=[
            ConditionResultResponse(
                field=c.field,
                op=c.op,
                expected=c.expected,
                actual=c.actual,
                match=c.match,
            )
            for c in decision.when_conditions
        ],
        policy_id=policy_id,
        endpoint=body.endpoint,
        method=body.method,
        rules=rules,
        agent_metadata=agent_metadata,
    )
