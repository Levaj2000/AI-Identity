"""Pydantic schemas for the compliance export API.

See ``docs/ADR-002-compliance-exports.md`` for the full design rationale
and per-field semantics. This module is the authoritative contract —
the router uses these models for request validation and response
shape, and OpenAPI surfaces them to downstream consumers (dashboard,
CLI, customer integrations) that need to write against a stable shape
while the builder is still being implemented.

Three public models plus a few supporting ones:

* :class:`ExportProfile` — the enum of supported framework profiles
* :class:`ExportCreateRequest` — POST body
* :class:`ExportResponse` — GET/POST response + list item shape
* :class:`ExportListResponse` — GET list response envelope
"""

from __future__ import annotations

import datetime  # noqa: TC003 — used by Pydantic at model-build time
import enum
import uuid  # noqa: TC003 — used by Pydantic at model-build time

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Max export window — see Cost guardrails section of the ADR.
# 18 months covers a standard 12-month SOC 2 Type II window plus a
# reasonable lookback buffer without letting a naive client dump
# everything since genesis.
MAX_AUDIT_PERIOD_DAYS = 548  # ~18 months


class ExportProfile(enum.StrEnum):
    """Supported compliance frameworks.

    Values are stable identifiers that show up in the API, in the
    manifest's ``profile`` field, and in the signed-URL path. Adding
    a framework is additive; renaming one breaks existing clients and
    is avoided unless coordinated.
    """

    soc2_tsc_2017 = "soc2_tsc_2017"
    eu_ai_act_2024 = "eu_ai_act_2024"
    nist_ai_rmf_1_0 = "nist_ai_rmf_1_0"


class ExportStatus(enum.StrEnum):
    """Job status values. Four-state FSM: queued → building → ready|failed."""

    queued = "queued"
    building = "building"
    ready = "ready"
    failed = "failed"


class ExportCreateRequest(BaseModel):
    """POST /api/v1/exports body."""

    model_config = ConfigDict(extra="forbid")

    profile: ExportProfile = Field(
        description="The compliance framework this export targets.",
    )
    audit_period_start: datetime.datetime = Field(
        description="UTC start of the audit period (inclusive). Must be timezone-aware.",
    )
    audit_period_end: datetime.datetime = Field(
        description="UTC end of the audit period (inclusive). Must be timezone-aware.",
    )
    agent_ids: list[uuid.UUID] | None = Field(
        default=None,
        description=(
            "Optional subset of agents to include (for targeted sampling-plan "
            "exports). Null or absent → whole org. Every id must belong to the "
            "caller's org; mixed-tenant requests are rejected at 400."
        ),
    )

    @model_validator(mode="after")
    def _validate_period(self) -> ExportCreateRequest:
        start = self.audit_period_start
        end = self.audit_period_end
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("audit_period_start and audit_period_end must be timezone-aware")
        if end <= start:
            raise ValueError("audit_period_end must be strictly after audit_period_start")
        span = end - start
        if span.days > MAX_AUDIT_PERIOD_DAYS:
            raise ValueError(
                f"audit period exceeds the {MAX_AUDIT_PERIOD_DAYS}-day maximum "
                "(covers 12-month SOC 2 Type II windows plus buffer); narrow the "
                "range or split into multiple exports"
            )
        return self


class ExportError(BaseModel):
    """Structured error detail populated on ``status == "failed"``.

    Separate from HTTP error bodies (which keep the existing
    ``{"error": {"code": str, "message": str}}`` shape). This one
    travels inside the :class:`ExportResponse` so clients can reason
    about *why* a build failed after it was accepted.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        description=(
            "Stable error code. Known codes include: "
            "``build_timeout``, ``archive_too_large``, ``storage_write_failed``, "
            "``kms_sign_failed``, ``source_data_unavailable``. The "
            "``infrastructure_*`` prefix denotes codes that page the on-call."
        ),
    )
    message: str = Field(description="Human-readable error detail.")


class ExportResponse(BaseModel):
    """The canonical export-job shape.

    Used as the response body for ``POST /api/v1/exports`` (status
    will typically be ``queued`` unless the builder is synchronous,
    which it is not) and ``GET /api/v1/exports/{id}``, and as the list
    item shape on ``GET /api/v1/exports``.

    Fields are populated conditionally on ``status`` — see the ADR for
    the state machine. Optional fields are ``None`` until reachable.
    """

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    org_id: uuid.UUID
    requested_by: uuid.UUID = Field(description="User id of the caller who requested the export.")
    profile: ExportProfile
    audit_period_start: datetime.datetime
    audit_period_end: datetime.datetime
    agent_ids: list[uuid.UUID] | None = None

    status: ExportStatus
    progress_pct: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Worker-reported build progress. Populated only while building.",
    )

    archive_url: str | None = Field(
        default=None,
        description="Signed GCS URL. Populated when status == ready. TTL: 1 hour.",
    )
    archive_url_expires_at: datetime.datetime | None = None
    archive_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 of the archive bytes. Populated when status == ready.",
    )
    archive_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Archive size in bytes. Populated when status == ready.",
    )

    manifest_envelope: dict | None = Field(
        default=None,
        description=(
            "DSSE envelope over the archive's manifest.json. Same shape as "
            "forensic_attestations.envelope; payloadType is "
            "'application/vnd.ai-identity.export-manifest+json'."
        ),
    )

    created_at: datetime.datetime
    completed_at: datetime.datetime | None = None

    error: ExportError | None = None


class ExportListResponse(BaseModel):
    """GET /api/v1/exports response envelope."""

    model_config = ConfigDict(extra="forbid")

    items: list[ExportResponse]
    next_cursor: str | None = Field(
        default=None,
        description=(
            "Opaque cursor for pagination. Pass back as the ``before`` query "
            "param to fetch the next page. Null when there are no more items."
        ),
    )
