"""Versioned schema for ``audit_log.request_metadata``.

Today ``request_metadata`` is an untyped JSONB blob — every call site
writes a different shape. ``AuditMetadataV1`` is the first typed contract:
opt-in for new code, backward-compatible for the legacy loose-dict rows
still sitting in the table.

The writer accepts either form:

  * ``dict``                — legacy path. Stored as-is after sanitization.
  * ``AuditMetadataV1``     — structured. ``model_dump()``'d into the JSONB
    column and tagged with ``schema_version: 1`` so readers can branch.

Reader code (``/audit`` endpoints, forensic reports, Seer analysis)
continues to treat the field as a dict; v1 rows just have more predictable
keys. A future v2 can add required fields — this release is a bridge.

Philosophy — required vs. optional:
  * ``schema_version`` is the only always-required field.
  * Everything else is optional in v1, because retrofitting all ~dozen
    existing call sites into a strict shape in one PR would be churn.
    Over successive PRs, call sites migrate to populate more fields.
    v2 (future) can promote some of these to required once adoption catches up.
"""

from __future__ import annotations

import uuid  # noqa: TC003 — used by Pydantic at model-build time, not only in types
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION_KEY = "schema_version"
CURRENT_SCHEMA_VERSION = 1


class Actor(BaseModel):
    """Who initiated the request.

    Separate from ``tenant`` because the same user can act across orgs
    (platform admin, support impersonation) and the same org can be
    acted on by service accounts.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["user", "service_account", "system"] = Field(
        description="Principal class. user = human; service_account = automated; system = AI Identity itself (e.g. scheduled jobs)."
    )
    id: str = Field(
        max_length=255,
        description="Stable identifier for the principal (UUID for users, email for service accounts, constant for system).",
    )
    email: str | None = Field(
        default=None,
        max_length=255,
        description="Optional display email. Not used for access control — denormalized for forensics readability.",
    )


class Tenant(BaseModel):
    """Which org + user this audit event belongs to.

    ``org_id`` is the enterprise-level scope (matches ``audit_log.org_id``
    at the column level — included here so exported metadata is
    self-describing without a JOIN).
    """

    model_config = ConfigDict(extra="forbid")

    org_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class PolicyTrace(BaseModel):
    """What the policy engine did, in enough detail to replay the decision.

    Mirrors the shape returned by the policy dry-run endpoint so a deny
    captured in an audit row can be diff'd against a fresh evaluation.
    """

    model_config = ConfigDict(extra="allow")

    matched_rules: list[str] = Field(
        default_factory=list,
        description="Policy rule IDs that matched this request (in evaluation order).",
    )
    when_conditions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="ABAC when-clause evaluations — kept loosely typed in v1, will be tightened in v2.",
    )
    dry_run: bool = Field(
        default=False,
        description="True if the policy was evaluated without enforcement (e.g. via /policy/evaluate).",
    )
    deny_reason: str | None = Field(
        default=None,
        description="Machine-readable deny code from DenyReason enum; absent on allows.",
    )


class Resource(BaseModel):
    """What the request targeted.

    Optional today — not every request has a clean resource shape (e.g.
    chat completions). Used mostly for lifecycle events (agent_created,
    key_rotated, policy_updated) where the before/after state is useful
    for a forensic timeline.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        max_length=64,
        description="Resource kind: 'agent', 'policy', 'credential', 'org', etc.",
    )
    id: str | None = Field(default=None, max_length=255)
    old_status: str | None = Field(default=None, max_length=64)
    new_status: str | None = Field(default=None, max_length=64)


class Cost(BaseModel):
    """Model / token / dollar context for AI API calls.

    Separated from the top-level ``cost_estimate_usd`` column on AuditLog
    — that stays authoritative for billing; this adds the breakdown.
    """

    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, max_length=128)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimate_usd: float | None = Field(default=None, ge=0.0)


class AuditMetadataV1(BaseModel):
    """Versioned, structured shape for ``audit_log.request_metadata``.

    Round-trip contract: ``AuditMetadataV1.model_validate(row_dict)`` must
    succeed for any row written via this model. Legacy rows (no
    ``schema_version`` key) fail validation — use ``is_v1(row_dict)``
    before attempting to parse.

    Unknown top-level keys are allowed (``extra="allow"``) so existing
    callers that write keys like ``action_type``, ``keys_revoked``,
    ``blocked_reason`` don't lose data when they migrate onto this model.
    Those loose keys will move into typed slots in a later schema revision.
    """

    model_config = ConfigDict(extra="allow")

    schema_version: Literal[1] = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Schema revision. Readers branch on this key — never omit.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=64,
        description="End-to-end request ID. Also denormalized on audit_log.correlation_id for fast indexed lookups.",
    )
    actor: Actor | None = None
    tenant: Tenant | None = None
    policy_trace: PolicyTrace | None = None
    resource: Resource | None = None
    cost: Cost | None = None
    latency_ms: int | None = Field(default=None, ge=0)


def is_v1(metadata: dict[str, Any] | None) -> bool:
    """True if a metadata dict carries the v1 schema tag.

    Use this before calling ``AuditMetadataV1.model_validate`` on stored
    rows to avoid raising on legacy loose-dict entries.
    """
    if not metadata:
        return False
    return metadata.get(SCHEMA_VERSION_KEY) == CURRENT_SCHEMA_VERSION


def as_metadata_dict(value: AuditMetadataV1 | dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a caller's metadata argument into a plain dict for DB storage.

    * ``None`` → ``{}``
    * ``AuditMetadataV1`` → ``model_dump(mode="json", exclude_none=True)``
      with ``schema_version`` always present.
    * ``dict`` → returned as-is (legacy path). No schema_version stamp —
      readers treat unstamped rows as pre-v1.
    """
    if value is None:
        return {}
    if isinstance(value, AuditMetadataV1):
        dumped = value.model_dump(mode="json", exclude_none=True)
        dumped[SCHEMA_VERSION_KEY] = CURRENT_SCHEMA_VERSION
        return dumped
    return value
