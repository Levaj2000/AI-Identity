"""Pydantic v2 schemas for the audit-forwarding sink API."""

from __future__ import annotations

import datetime  # noqa: TC003 — used by Pydantic at model-build time
import uuid  # noqa: TC003 — used by Pydantic at model-build time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Filter sub-schema ────────────────────────────────────────────────


class SinkFilter(BaseModel):
    """Optional per-sink filter — forward only events matching these criteria.

    Empty / omitted = forward everything. Both lists, if present, use OR
    within themselves and AND across themselves (all conditions must match).
    """

    model_config = ConfigDict(extra="forbid")

    decisions: list[Literal["allow", "deny", "error"]] | None = Field(
        default=None,
        description="Only forward events with one of these decisions.",
    )
    action_types: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Only forward events whose request_metadata.action_type is in this list.",
    )


# ── Create ───────────────────────────────────────────────────────────


class SinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=120, min_length=1)
    kind: Literal["webhook"] = Field(
        default="webhook",
        description="Transport kind. webhook is the only option today (issue #136 tracks follow-ups).",
    )
    url: str = Field(
        max_length=2048,
        description="Destination URL. MUST be https:// — http:// is rejected.",
    )
    description: str | None = Field(default=None, max_length=1000)
    filter: SinkFilter = Field(default_factory=SinkFilter)
    # Secret is generated server-side if not supplied — see POST handler.
    secret: str | None = Field(
        default=None,
        max_length=128,
        min_length=32,
        description=(
            "HMAC signing secret (hex, 32-128 chars). Omit to have one generated "
            "server-side. Shown in the response once; not returned on subsequent GETs."
        ),
    )

    @field_validator("url")
    @classmethod
    def _reject_non_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("url must start with https://")
        return v


# ── Update ───────────────────────────────────────────────────────────


class SinkUpdate(BaseModel):
    """Partial update — all fields optional."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120, min_length=1)
    url: str | None = Field(default=None, max_length=2048)
    description: str | None = Field(default=None, max_length=1000)
    filter: SinkFilter | None = None
    enabled: bool | None = None
    rotate_secret: bool = Field(
        default=False,
        description=(
            "If true, generates a new secret and returns it in the response. "
            "Old secret is discarded — no grace window in this release "
            "(tracked in #136)."
        ),
    )

    @field_validator("url")
    @classmethod
    def _reject_non_https(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("https://"):
            raise ValueError("url must start with https://")
        return v


# ── Response ─────────────────────────────────────────────────────────


class SinkResponse(BaseModel):
    """Read-shape for a sink. Secret is NEVER returned after creation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    kind: str
    url: str
    description: str | None
    enabled: bool
    filter: dict[str, Any] = Field(
        default_factory=dict,
        description="Current filter_config. Shape matches SinkFilter.",
    )
    consecutive_failures: int
    circuit_opened_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    created_by: uuid.UUID


class SinkCreatedResponse(SinkResponse):
    """One-time response on create or rotate-secret — includes the secret.

    The caller MUST capture this value; we never return it again.
    """

    secret: str = Field(
        description="HMAC signing secret. Store in your webhook receiver — AI Identity will not show it again."
    )


class SinkListResponse(BaseModel):
    items: list[SinkResponse]
    total: int


# ── Test delivery ────────────────────────────────────────────────────


class SinkTestResponse(BaseModel):
    """Result of a synthetic test delivery to a sink."""

    sink_id: uuid.UUID
    delivered: bool
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None
