"""Pydantic v2 schemas for the forensic retention policy plane (v0.5.0).

Request/response shapes for the retention policy API: policy CRUD with
create-time validation, the explain endpoint, legal holds, and the
retention-event feed.

Design authority: Notion "Forensic Retention Policies — Policy Model (v0.5.0)".
Semantic validation (durations, shadow detection, tier ceilings,
shortening friction) lives in :mod:`common.validation.retention`; these
schemas only describe the wire shapes.
"""

from __future__ import annotations

import datetime  # noqa: TC003 — needed at runtime for pydantic Field type resolution
import uuid  # noqa: TC003  — needed at runtime for pydantic Field type resolution
from typing import Any

from pydantic import BaseModel, Field

# ── Rules ────────────────────────────────────────────────────────────────


class RetentionSampling(BaseModel):
    """Deterministic sampling ratio pinned inside the immutable policy version."""

    alg: str = Field(description='Sampling algorithm; v0.5.0 pins "sha256-mod-v1".')
    of: int = Field(gt=0, description="Denominator of the sampling ratio.")
    keep: int = Field(gt=0, description="Numerator: keep this many out of `of`.")


class RetentionRule(BaseModel):
    """One first-match rule in a retention policy's ordered rule array."""

    rule_id: str = Field(description="Stable rule identifier, unique within the policy.")
    selector: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Match predicate. Whitelisted keys: record_class, flow_tag, decision, "
            "agent_id, session_id, risk_tier, event_type. List values are "
            "allowed-value sets; scalars are single allowed values. An empty "
            "selector matches everything (the required terminal catch-all)."
        ),
    )
    retain_for: str = Field(
        description='ISO-8601 duration restricted to days/weeks/years (e.g. "P90D"), or "indefinite".'
    )
    redact_after: str | None = Field(
        default=None,
        description="Optional second clock; must be strictly less than retain_for.",
    )
    sampling: RetentionSampling | None = Field(
        default=None, description="Optional sampling ratio; omitted means keep_all."
    )
    hold_exempt: bool = Field(
        default=False, description="Reserved; legal holds are ceiling-exempt regardless."
    )


class ApprovalEntry(BaseModel):
    """One approval on a policy version. `by` is an opaque principal ID, never an email."""

    by: str = Field(description="Opaque principal ID of the approver.")
    at: datetime.datetime = Field(description="When the approval was recorded.")


class RetentionPolicyCreate(BaseModel):
    """Request body for creating a new retention policy version."""

    rules: list[RetentionRule] = Field(
        min_length=1,
        description="Ordered rules, first-match. Must end with a terminal catch-all.",
    )
    default_rule: dict[str, Any] = Field(
        description='Fallback applied when no rule matches, e.g. {"retain_for": "P30D"}.'
    )
    change_reason: str | None = Field(default=None, description="Why this version exists.")
    approvals: list[ApprovalEntry] = Field(
        default_factory=list,
        description="Dual-approval trail; required (≥2 distinct principals) when shortening.",
    )
    effective_at: datetime.datetime | None = Field(
        default=None,
        description=(
            "When this version takes effect. Shortening versions default to now+7d "
            "and may not take effect sooner."
        ),
    )


class RetentionPolicyResponse(BaseModel):
    """One immutable retention policy version."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    policy_id: str
    org_id: uuid.UUID
    version: int
    status: str
    rules: list[dict[str, Any]]
    default_rule: dict[str, Any]
    created_by: str
    created_at: datetime.datetime
    effective_at: datetime.datetime
    supersedes: uuid.UUID | None
    change_reason: str | None
    approvals: list[dict[str, Any]]
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal validation findings (e.g. broad-before-narrow).",
    )


# ── Explain ──────────────────────────────────────────────────────────────


class ExplainRequest(BaseModel):
    """A record descriptor to match against the active policy's rules.

    Every field is optional; a selector key only matches when the descriptor
    carries that key.
    """

    record_class: str | None = None
    flow_tag: str | None = None
    decision: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    risk_tier: str | None = None
    event_type: str | None = None


class ExplainResponse(BaseModel):
    """The first matching rule for a descriptor under the active policy."""

    rule_id: str
    rule: dict[str, Any]
    matched_index: int = Field(description="0-based index into the active policy's rule array.")


# ── Legal holds ──────────────────────────────────────────────────────────


class HoldCreate(BaseModel):
    """Request body for placing a legal hold."""

    selector: dict[str, Any] = Field(
        description=(
            "Hold selector: record_ids, agent_id, and/or a time_window "
            "{from, to}, plus class and flow_tag. Empty fields are wildcards."
        ),
    )


class HoldRelease(BaseModel):
    """Request body for releasing a legal hold."""

    release_reason: str = Field(description="Why the hold is being released.")


class HoldResponse(BaseModel):
    """A legal hold."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    org_id: uuid.UUID
    selector: dict[str, Any]
    status: str
    placed_by: str
    placed_at: datetime.datetime
    released_at: datetime.datetime | None
    released_by: str | None
    release_reason: str | None


# ── Retention events ─────────────────────────────────────────────────────


class RetentionEventResponse(BaseModel):
    """One row of the retention_event record class."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    org_id: uuid.UUID
    event_type: str
    payload: dict[str, Any]
    created_by: str
    created_at: datetime.datetime
