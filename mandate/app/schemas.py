"""Pydantic schemas for mandate documents and API I/O.

Mandate lifecycle:
  active   — valid within [valid_from, valid_until), all signatures verified
  revoked  — explicitly cancelled; revocation record attached
  expired  — past valid_until; flipped by the expiry sweeper cron
  exceeded — spend limit breached via the settlement path; exceedance record attached

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
    exceeded = "exceeded"  # spend limit breached (settlement path) — terminal, like revoked


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


class SpendLimit(BaseModel):
    """Monetary authority carried by the mandate (part of the signed grant).

    Amounts are integer cents — never floats — so the limit survives
    canonicalization byte-for-byte and no rounding ambiguity reaches the
    signature. `window` is fixed to lifetime-total for now; per-period
    windows (daily/monthly) are a reserved extension, not implemented.
    """

    limit_cents: int = Field(gt=0, description="Maximum cumulative spend, integer cents")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    window: str = Field(default="total", description="Only 'total' is supported today")

    @field_validator("window")
    @classmethod
    def window_supported(cls, v: str) -> str:
        if v != "total":
            raise ValueError("only window='total' is supported")
        return v


class MandateExceedance(BaseModel):
    """Runtime record of a spend-limit breach (NOT part of the signed grant)."""

    exceeded_at: datetime
    attempted_cents: int = Field(description="The spend that crossed the limit")
    spent_cents: int = Field(description="Cumulative spend at breach time")
    limit_cents: int
    reference: str | None = Field(None, description="Caller reference, e.g. order id")


# ── Core document ─────────────────────────────────────────────────────────


class MandateDocument(BaseModel):
    """Canonical MongoDB document shape for a mandate."""

    mandate_id: str = Field(description="Human-readable ID: mnd_<8-char-hex>")
    schema_version: str = "1.1"
    status: MandateStatus = MandateStatus.active

    issuer: MandateIssuer
    subject: MandateSubject

    scope: list[str] = Field(description="Permission scopes, e.g. ['read:audit', 'write:policies']")
    conditions: dict[str, Any] = Field(
        default_factory=dict, description="ABAC conditions (env, tier, etc.)"
    )
    policy_hash: str | None = Field(None, description="SHA-256 of the linked policy rules JSON")
    spend_limit: SpendLimit | None = Field(
        None, description="Monetary authority — part of the signed grant"
    )

    valid_from: datetime
    valid_until: datetime | None = None

    signatures: list[MandateSignature] = Field(default_factory=list)
    revocation: MandateRevocation | None = None

    # Runtime state — NOT part of the signed grant (schema >= 1.1 excludes
    # these from the signable payload; see signing._build_signable_payload).
    spent_cents: int = Field(default=0, ge=0)
    exceedance: MandateExceedance | None = None

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
    spend_limit: SpendLimit | None = None
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


class RecordSpendRequest(BaseModel):
    """Body for POST /api/v1/mandates/{id}/spend.

    Two modes:
      settlement=False (default) — ENFORCE: a spend that would cross the
        limit is rejected (not recorded) and the mandate stays active with
        its remaining budget intact.
      settlement=True — RECORD: the money already moved (e.g. a payment-
        processor webhook); the spend is recorded even if it crosses the
        limit, and a crossing flips the mandate to `exceeded`.
    """

    amount_cents: int = Field(gt=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    description: str | None = Field(None, max_length=200)
    reference: str | None = Field(None, max_length=100, description="e.g. order id")
    settlement: bool = False


class RecordSpendResult(BaseModel):
    mandate_id: str
    accepted: bool = Field(description="Whether the spend was recorded")
    exceeded: bool = Field(description="Whether this call breached the limit")
    status: MandateStatus
    spent_cents: int
    limit_cents: int | None
    remaining_cents: int | None
    deny_reason: str | None = None


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
    spend_limit: SpendLimit | None = None
    valid_from: datetime
    valid_until: datetime | None
    signatures: list[MandateSignature]
    revocation: MandateRevocation | None
    spent_cents: int = 0
    exceedance: MandateExceedance | None = None
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
        description=(
            "Individual check results: signatures_valid, status_active, "
            "not_expired, scope_sufficient, within_spend_limit"
        )
    )
    error: str | None = None
