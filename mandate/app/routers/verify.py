"""Offline mandate verification endpoint.

Accepts a full mandate payload (as returned by GET /mandates/:id) and
runs all validity checks without needing to re-query MongoDB. Useful for:
  - Gateway enforcement: verify a mandate bundle presented by an agent
  - Offline compliance checks: audit tools verifying stored mandates
  - Cross-org verification: a recipient org verifying a presented mandate

Checks performed:
  1. signatures_valid   — all classical signatures verify against payload
  2. status_active      — status == "active"
  3. not_expired        — valid_until is None OR now < valid_until
  4. scope_sufficient   — if required_scope provided, mandate.scope is a superset
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Query

from mandate.app.schemas import (
    MandateDocument,
    MandateStatus,
    VerifyMandateRequest,
    VerifyMandateResult,
)
from mandate.app.signing import verify_signature

logger = logging.getLogger("ai_identity.mandate.verify")

router = APIRouter(prefix="/api/v1/mandates", tags=["mandates"])


@router.post("/verify", response_model=VerifyMandateResult, summary="Verify a mandate bundle")
async def verify_mandate(
    body: VerifyMandateRequest,
    required_scope: list[str] | None = Query(None, description="Scopes the mandate must cover"),
):
    """Verify a mandate payload without a live MongoDB lookup.

    This endpoint is intentionally unauthenticated so gateway sidecars and
    external verifiers can call it without developer credentials. It does not
    return any stored data — only a verdict on the submitted payload.

    To prevent spoofing: the signature check is the authority. A mandate with
    invalid signatures is rejected even if all other fields look correct.
    """
    mandate_resp = body.mandate
    mandate_id = mandate_resp.mandate_id

    # Reconstruct the MandateDocument for signature verification
    mandate = MandateDocument(**mandate_resp.model_dump())

    checks: dict[str, bool] = {}
    errors: list[str] = []

    # 1. Signature check
    #
    # verify_signature returns True / False / None where None means
    # "algorithm not verifiable by this version" (e.g. the ml-dsa-87 slot).
    # We require: at least one signature must be verifiable AND every
    # verifiable signature must pass. This keeps hybrid mandates working
    # (classical + future-algo slot) while closing the spoofing path of
    # submitting a mandate with only unknown-algorithm signatures.
    if not mandate.signatures:
        checks["signatures_valid"] = False
        errors.append("No signatures present")
    else:
        sig_results = [await verify_signature(mandate, sig) for sig in mandate.signatures]
        verifiable = [r for r in sig_results if r is not None]
        if not verifiable:
            checks["signatures_valid"] = False
            errors.append("No verifiable signature algorithms on this mandate")
        elif not all(verifiable):
            checks["signatures_valid"] = False
            errors.append("One or more signatures are invalid")
        else:
            checks["signatures_valid"] = True

    # 2. Status check
    checks["status_active"] = mandate.status == MandateStatus.active
    if not checks["status_active"]:
        errors.append(f"Mandate status is '{mandate.status.value}', not 'active'")

    # 3. Expiry check
    now = datetime.now(UTC)
    if mandate.valid_until is None:
        checks["not_expired"] = True
    else:
        # Ensure valid_until is timezone-aware for comparison
        vu = mandate.valid_until
        if vu.tzinfo is None:
            vu = vu.replace(tzinfo=UTC)
        checks["not_expired"] = now < vu
        if not checks["not_expired"]:
            errors.append(f"Mandate expired at {vu.isoformat()}")

    # 4. Scope check (only if caller specified required_scope)
    if required_scope:
        mandate_scope_set = set(mandate.scope)
        required_set = set(required_scope)
        checks["scope_sufficient"] = required_set.issubset(mandate_scope_set)
        if not checks["scope_sufficient"]:
            missing = required_set - mandate_scope_set
            errors.append(f"Missing required scopes: {sorted(missing)}")
    else:
        checks["scope_sufficient"] = True

    valid = all(checks.values())
    return VerifyMandateResult(
        valid=valid,
        mandate_id=mandate_id,
        checks=checks,
        error="; ".join(errors) if errors else None,
    )
