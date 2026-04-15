"""Pydantic schemas for the policy dry-run evaluation endpoint.

The endpoint accepts two request shapes:

1. Bound to a real agent: ``{agent_id, endpoint, method}`` — the evaluator
   looks up the agent's active policy and metadata and evaluates.

2. What-if mode: ``{agent_metadata, rules, endpoint, method}`` — the caller
   supplies hypothetical metadata and a candidate rules dict, nothing is
   persisted, nothing references a real agent. Useful for policy authoring
   and dashboard-side "try it" flows.

The response surfaces the full :class:`PolicyDecision` including the
per-condition ``when`` trace so the caller can show exactly why a request
was allowed or denied.
"""

from __future__ import annotations

import uuid  # noqa: TC003  — needed at runtime for pydantic Field type resolution
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ── Request ──────────────────────────────────────────────────────────────────


class PolicyEvaluateRequest(BaseModel):
    """Request body for ``POST /api/v1/policy/evaluate``.

    Must supply EITHER ``agent_id`` OR (``agent_metadata`` AND ``rules``).
    Mixing modes is rejected to keep the semantics unambiguous.
    """

    agent_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional. Evaluate against the active policy of this agent. "
            "The caller must own the agent (or share its org). "
            "Mutually exclusive with `rules`."
        ),
    )
    agent_metadata: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional. Hypothetical agent metadata for what-if testing. "
            "If `agent_id` is given, this is ignored — the real agent's "
            "metadata is used."
        ),
    )
    rules: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional. Candidate policy rules to evaluate. Required if "
            "`agent_id` is not given. Ignored if `agent_id` is given."
        ),
    )
    endpoint: str = Field(
        description="Target API endpoint (e.g. /v1/chat).",
        min_length=1,
        max_length=256,
    )
    method: str = Field(
        description="HTTP method (e.g. GET, POST).",
        min_length=1,
        max_length=16,
    )

    @model_validator(mode="after")
    def _one_mode_or_the_other(self) -> PolicyEvaluateRequest:
        has_agent = self.agent_id is not None
        has_rules = self.rules is not None
        if has_agent and has_rules:
            msg = "Supply either `agent_id` or `rules`, not both."
            raise ValueError(msg)
        if not has_agent and not has_rules:
            msg = "Must supply either `agent_id` or `rules` (what-if mode)."
            raise ValueError(msg)
        return self


# ── Response ─────────────────────────────────────────────────────────────────


class ConditionResultResponse(BaseModel):
    """Per-condition trace from a ``when`` clause evaluation."""

    field: str
    op: str
    expected: Any
    actual: Any
    match: bool


class PolicyEvaluateResponse(BaseModel):
    """Response body for the dry-run endpoint.

    Mirrors :class:`common.policy.eval.PolicyDecision` with the rule set and
    context echoed back so the caller has a self-contained record of what
    was evaluated.
    """

    allowed: bool = Field(description="Overall decision.")
    deny_reason: str | None = Field(
        default=None,
        description=(
            "Stable rule identifier if denied. Formats include "
            "`when:<field>:not_equal:...`, `allowed_endpoints:not_matched:...`, "
            "`denied_endpoints:<pattern>`, `allowed_methods:not_allowed:...`."
        ),
    )
    matched_rule: str | None = Field(
        default=None,
        description="Which rule fired — the allowed-endpoint on allow, the denial rule on deny.",
    )
    when_conditions: list[ConditionResultResponse] = Field(
        default_factory=list,
        description="Each condition in the `when` clause with expected vs. actual.",
    )
    policy_id: int | None = Field(
        default=None,
        description="The evaluated policy's row id (only for agent-bound mode).",
    )
    endpoint: str
    method: str
    rules: dict[str, Any] = Field(
        description="The rules dict that was evaluated (echoed for caller clarity).",
    )
    agent_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="The metadata dict used for `when` evaluation.",
    )
