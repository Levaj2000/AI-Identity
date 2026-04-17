"""Forensic attestation sign endpoint.

``POST /api/v1/attestations`` closes out a session by:

1. Resolving the caller's session window to a concrete range of
   ``audit_log`` rows (by ``[first_audit_id, last_audit_id]`` inclusive).
2. Reading the tail row's ``entry_hash`` as the committed chain hash.
3. Building an :class:`AttestationPayloadV1`, JCS-canonicalizing it,
   and signing via the configured backend (GCP KMS in prod, local PEM
   in dev/test).
4. Persisting the full DSSE envelope plus the resolved row IDs to
   ``forensic_attestations``. The resolved IDs let a verifier detect
   "chain existed at sign time, N rows missing now" after retention
   purges — see the Retention coordination section of the design doc.

Idempotency: ``(org_id, session_id)`` is UNIQUE. If the client retries,
we return the existing envelope with 200 — never produce a second
conflicting attestation for the same session.

AuthZ: the caller must be an owner/admin of the org identified in the
request body. Platform admins (``user.role == "admin"``) also pass,
for the ops paths that need to sign on behalf of a tenant.
"""

from __future__ import annotations

import logging
import time
import uuid  # noqa: TC003 — used at runtime by Pydantic model fields
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from api.app.auth import get_current_user
from common.forensic import (
    ForensicSignerConfigError,
    SignerHandle,
    get_forensic_signer,
)
from common.models import (
    AuditLog,
    ForensicAttestation,
    OrgMembership,
    User,
    get_db,
)
from common.observability.metrics import (
    attestation_sign_latency_ms,
    attestation_signs_total,
)
from common.schemas.forensic_attestation import (
    AttestationPayloadV1,
    DSSEEnvelope,
    sign_payload,
)

logger = logging.getLogger("ai_identity.api.attestations")

router = APIRouter(prefix="/api/v1/attestations", tags=["attestations"])

# Cache the signer handle for the process lifetime. The KMS client
# creates its own gRPC channel on first use; we don't want to rebuild
# it per request. Failures are latched to None so a misconfigured
# service still returns 503 rather than crashing on every call.
_signer_handle: SignerHandle | None = None
_signer_handle_error: str | None = None


def _get_signer() -> SignerHandle:
    """Resolve the signer once per process, raising 503 on config errors."""
    global _signer_handle, _signer_handle_error
    if _signer_handle is not None:
        return _signer_handle
    if _signer_handle_error is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"forensic signer unavailable: {_signer_handle_error}",
        )
    try:
        _signer_handle = get_forensic_signer()
        return _signer_handle
    except ForensicSignerConfigError as exc:
        _signer_handle_error = str(exc)
        attestation_signs_total.labels(backend="unknown", outcome="config_error").inc()
        logger.error("forensic signer not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"forensic signer unavailable: {exc}",
        ) from exc


def _reset_signer_cache_for_tests() -> None:
    """Test-only hook to re-read settings after monkey-patching."""
    global _signer_handle, _signer_handle_error
    _signer_handle = None
    _signer_handle_error = None


# ── Request / response models ─────────────────────────────────────────


class AttestationSignRequest(BaseModel):
    """Caller-supplied inputs for a session-close sign.

    The range of audit rows is identified by the session window
    (``session_start`` / ``session_end``) plus explicit bounds
    (``first_audit_id`` / ``last_audit_id``). We take both because
    producers already know their window — forcing the server to "guess"
    from timestamps alone invites off-by-one errors at session
    boundaries and creates ambiguity when multiple sessions overlap in
    time. The bounds win on disagreement; timestamps are metadata.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: uuid.UUID = Field(
        description="Opaque producer identifier for the session being closed.",
    )
    org_id: uuid.UUID = Field(
        description="The org whose audit chain is being attested.",
    )
    first_audit_id: int = Field(
        ge=1,
        description="First audit_log.id to include (inclusive).",
    )
    last_audit_id: int = Field(
        ge=1,
        description="Last audit_log.id to include (inclusive).",
    )
    session_start: datetime = Field(
        description="UTC start of the session window.",
    )
    session_end: datetime = Field(
        description="UTC end of the session window.",
    )


class AttestationResponse(BaseModel):
    """A signed attestation record as returned by POST + (future) GET."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    org_id: uuid.UUID
    session_id: uuid.UUID
    first_audit_id: int
    last_audit_id: int
    event_count: int
    session_start: datetime
    session_end: datetime
    signed_at: datetime
    signer_key_id: str
    envelope: DSSEEnvelope


# ── AuthZ helper ──────────────────────────────────────────────────────


def _assert_org_admin(db: Session, user: User, org_id: uuid.UUID) -> None:
    """Raise 403 unless the user is an owner/admin of ``org_id`` (or a
    platform admin). Kept narrow — attestation signing is a destructive
    operation in the trust-model sense (it's a permanent claim) so we
    don't let arbitrary org members trigger it.
    """
    if user.role == "admin":
        return
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.role.in_(("owner", "admin")),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="org membership required to sign attestations for this org",
        )


# ── Endpoint ──────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=AttestationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign a forensic attestation for a session's audit range",
)
def sign_attestation(
    body: AttestationSignRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AttestationResponse:
    _assert_org_admin(db, user, body.org_id)

    if body.last_audit_id < body.first_audit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="last_audit_id must be >= first_audit_id",
        )
    if body.session_end < body.session_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_end must be >= session_start",
        )

    # Idempotency: return the existing attestation if one already
    # exists for this (org, session). A client retry after a timeout
    # must never produce a second conflicting envelope.
    existing = (
        db.query(ForensicAttestation)
        .filter(
            ForensicAttestation.org_id == body.org_id,
            ForensicAttestation.session_id == body.session_id,
        )
        .first()
    )
    if existing is not None:
        return _to_response(existing)

    signer = _get_signer()

    # Resolve the range to concrete row IDs + the tail entry_hash.
    # Ordering by id ASC guarantees we get rows in chain order, which
    # is the order the HMAC chain was built in.
    rows = db.execute(
        select(AuditLog.id, AuditLog.entry_hash, AuditLog.org_id)
        .where(
            AuditLog.id >= body.first_audit_id,
            AuditLog.id <= body.last_audit_id,
        )
        .order_by(AuditLog.id.asc())
    ).all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"no audit_log rows in range [{body.first_audit_id}, {body.last_audit_id}]"),
        )

    # Enforce org isolation on every row — a caller must not be able to
    # attest over another tenant's chain by guessing ID ranges. This is
    # the row-level guardrail behind the membership check above.
    foreign = [row_id for (row_id, _h, o) in rows if o != body.org_id]
    if foreign:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"range contains {len(foreign)} audit_log row(s) belonging to "
                "another org; refusing to sign a mixed-tenant chain"
            ),
        )

    audit_log_ids = [row_id for (row_id, _h, _o) in rows]
    tail_hash = rows[-1][1]
    event_count = len(rows)

    signed_at = datetime.now(UTC)
    payload = AttestationPayloadV1(
        session_id=body.session_id,
        org_id=body.org_id,
        evidence_chain_hash=tail_hash,
        first_audit_id=body.first_audit_id,
        last_audit_id=body.last_audit_id,
        event_count=event_count,
        session_start=body.session_start,
        session_end=body.session_end,
        signed_at=signed_at,
        signer_key_id=signer.key_id,
    )

    t0 = time.perf_counter()
    try:
        envelope = sign_payload(payload, signer.sign)
    except Exception:
        attestation_signs_total.labels(backend=signer.backend, outcome="error").inc()
        logger.exception(
            "forensic sign failed",
            extra={"session_id": str(body.session_id), "org_id": str(body.org_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="signer backend returned an error",
        ) from None
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        attestation_sign_latency_ms.labels(backend=signer.backend).observe(elapsed_ms)

    attestation_signs_total.labels(backend=signer.backend, outcome="ok").inc()

    row = ForensicAttestation(
        org_id=body.org_id,
        session_id=body.session_id,
        first_audit_id=body.first_audit_id,
        last_audit_id=body.last_audit_id,
        event_count=event_count,
        audit_log_ids=audit_log_ids,
        session_start=body.session_start,
        session_end=body.session_end,
        signer_key_id=signer.key_id,
        signed_at=signed_at,
        envelope=envelope.model_dump(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Another request signed the same (org, session) between our
        # SELECT and INSERT. Roll back, fetch the winner, return it.
        db.rollback()
        winner = (
            db.query(ForensicAttestation)
            .filter(
                ForensicAttestation.org_id == body.org_id,
                ForensicAttestation.session_id == body.session_id,
            )
            .first()
        )
        if winner is None:  # pragma: no cover — should never happen
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="integrity error persisting attestation but no winner found",
            ) from None
        return _to_response(winner)
    db.refresh(row)
    return _to_response(row)


def _to_response(row: ForensicAttestation) -> AttestationResponse:
    return AttestationResponse(
        id=row.id,
        org_id=row.org_id,
        session_id=row.session_id,
        first_audit_id=row.first_audit_id,
        last_audit_id=row.last_audit_id,
        event_count=row.event_count,
        session_start=row.session_start,
        session_end=row.session_end,
        signed_at=row.signed_at,
        signer_key_id=row.signer_key_id,
        envelope=DSSEEnvelope.model_validate(row.envelope),
    )
