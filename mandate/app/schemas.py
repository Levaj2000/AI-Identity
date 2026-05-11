"""Pydantic schemas for mandate documents and API I/O.

Mandate lifecycle:
  active   — valid within [valid_from, valid_until), all signatures verified
  revoked  — explicitly cancelled; revocation record attached
  expired  — past valid_until; flipped by the expiry sweeper cron

Signature envelope is an array so we can carry multiple algorithms
simultaneously (classical + PQC hybrid). At launch only ecdsa-p256-sha256
is produced; the ml-dsa-87 slot is reserved for H2 PQC launch.
"""

from __future__ import annotations

# datetime is imported at runtime (not TYPE_CHECKING) so Pydantic can
# resolve forward references without an explicit model_rebuild() call.
from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ── Enums ─────────────────────────────────────────────────────────────────


class MandateStatus(StrEnum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class SignatureAlgorithm(StrEnum):
    ecdsa_p256_sha256 = "ecdsa-p256-sha256"  # classical — live at launch
    ml_dsa_87 = "ml-dsa-87"  # PQC — reserved, not yet issued


# ── Sub-documents ─────────────────────────────────────────────────────────


class MandateIssuer(BaseModel):
    org_id: str
    agent_id: str | None = None
    user_id: str | None = None


class MandateSubject(BaseModel):
    agent_id: str
    org_id: str


class MandateSignature(BaseModel):
    algorithm: SignatureAlgorithm
    key_id: str = Field(description="GCP KMS key-version resource name or 'local:<fingerprint>'")
    signature: str = Field(
        description="Base64url-encoded signature over the canonical mandate payload"
    )


class MandateRevocation(BaseModel):
    revoked_at: datetime
    revoked_by: str = Field(description="User ID who revoked")
    reason: str


# ── Core document ─────────────────────────────────────────────────────────


class MandateDocument(BaseModel):
    """Canonical MongoDB document shape for a mandate."""

    mandate_id: str = Field(description="Human-readable ID: mnd_<8-char-hex>")
    schema_version: str = "1.0"
    status: MandateStatus = MandateStatus.active

    issuer: MandateIssuer
    subject: MandateSubject

    scope: list[str] = Field(description="Permission scopes, e.g. ['read:audit', 'write:policies']")
    conditions: dict[str, Any] = Field(
        default_factory=dict, description="ABAC conditions (env, tier, etc.)"
    )
    policy_hash: str | None = Field(None, description="SHA-256 of the linked policy rules JSON")

    valid_from: datetime
    valid_until: datetime | None = None

    signatures: list[MandateSignature] = Field(default_factory=list)
    revocation: MandateRevocation | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("scope")
    @classmethod
    def scope_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("scope must contain at least one entry")
        return v


# ── API Request / Response models ─────────────────────────────────────────


class IssueMandateRequest(BaseModel):
    """Body for POST /api/v1/mandates."""

    subject_agent_id: str
    subject_org_id: str
    scope: list[str]
    conditions: dict[str, Any] = Field(default_factory=dict)
    policy_hash: str | None = None
    valid_from: datetime | None = None  # defaults to now
    valid_until: datetime | None = None  # None = no expiry
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scope")
    @classmethod
    def scope_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("scope must contain at least one entry")
        return v


class RevokeMandateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class MandateResponse(BaseModel):
    """API response — excludes internal MongoDB _id."""

    mandate_id: str
    schema_version: str
    status: MandateStatus
    issuer: MandateIssuer
    subject: MandateSubject
    scope: list[str]
    conditions: dict[str, Any]
    policy_hash: str | None
    valid_from: datetime
    valid_until: datetime | None
    signatures: list[MandateSignature]
    revocation: MandateRevocation | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MandateListResponse(BaseModel):
    mandates: list[MandateResponse]
    total: int
    page: int
    page_size: int


class VerifyMandateRequest(BaseModel):
    """Body for POST /api/v1/mandates/verify — accepts a full mandate payload."""

    mandate: MandateResponse


class VerifyMandateResult(BaseModel):
    valid: bool
    mandate_id: str
    checks: dict[str, bool] = Field(
        description="Individual check results: signatures_valid, status_active, not_expired, scope_sufficient"
    )
    error: str | None = None
