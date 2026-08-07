"""Biscuit mandate presentation + settlement at the gateway (demo tier).

Two-layer check for requests that present a mandate Biscuit
(``X-Agent-Mandate`` header):

  1. LOCAL, offline — verify the token's signature chain and run its
     Datalog checks (subject binding, scope, ceiling incl. attenuation,
     validity window) against the presented request. No network, no DB.
     This is where a sub-agent's narrowed ceiling denies an over-draw
     before the Mandate Service is ever consulted.
  2. SETTLEMENT — after policy ALLOW, draw against the authoritative
     mandate document via the Mandate Service (cumulative spend lives
     there, never in the token). Fail-closed behind its own circuit
     breaker: a Mongo/mandate-service hiccup must not trip the policy
     breaker for agents that aren't presenting mandates at all.

Demo-tier honesty (Phase 4 replaces both):
  - the draw call authenticates with a developer bearer token from
    settings.mandate_draw_token (same pattern as the existing demo
    script), not an agent-plane credential;
  - the verify key is derived from the shared root PEM rather than a
    distributed public key.
"""

import logging
from dataclasses import dataclass, field

import httpx

from common.biscuit import PresentationResult, authorize_presentation, root_public_key_hex
from common.config.settings import settings
from gateway.app.circuit_breaker import CircuitBreaker

logger = logging.getLogger("ai_identity.gateway.mandate_check")

# Separate breaker from the policy engine's — see module docstring.
mandate_circuit_breaker = CircuitBreaker(name="mandate-service")


@dataclass
class MandateCheckOutcome:
    allowed: bool
    status_code: int = 200
    deny_reason: str | None = None
    message: str = ""
    # Flat scalars destined for the audit chain (sanitizer-allowlisted keys).
    audit_metadata: dict = field(default_factory=dict)
    # Mandate Service draw response body (surfaced to the caller on success).
    draw: dict | None = None


def _presentation_metadata(presentation: PresentationResult) -> dict:
    meta: dict = {
        "credential_format": "biscuit",
        "biscuit_block_count": presentation.block_count,
    }
    if presentation.mandate_id:
        meta["mandate_id"] = presentation.mandate_id
    if presentation.revocation_ids:
        # The LAST id identifies the exact presented token (incl. attenuation).
        meta["biscuit_revocation_id"] = presentation.revocation_ids[-1]
    if presentation.deny_detail:
        meta["biscuit_deny_detail"] = presentation.deny_detail[:500]
    return meta


def check_presentation(
    token_b64: str,
    *,
    agent_id: str,
    amount_cents: int,
    scope: str,
    currency: str,
    settlement: bool = False,
) -> MandateCheckOutcome:
    """Layer 1 — verify and evaluate the presented Biscuit locally."""
    pem = settings.biscuit_root_key_pem
    if not pem.strip():
        return MandateCheckOutcome(
            allowed=False,
            status_code=503,
            deny_reason="mandate_unavailable",
            message="Biscuit trust anchor not configured on this gateway",
            audit_metadata={"credential_format": "biscuit"},
        )

    presentation = authorize_presentation(
        token_b64,
        root_public_key_hex(pem),
        agent_id=agent_id,
        amount_cents=amount_cents,
        scope=scope,
        currency=currency,
        settlement=settlement,
    )
    meta = _presentation_metadata(presentation)
    if not presentation.allowed:
        return MandateCheckOutcome(
            allowed=False,
            status_code=403,
            deny_reason="biscuit_denied",
            message="Mandate token rejected: " + (presentation.deny_detail or "invalid token"),
            audit_metadata=meta,
        )
    if presentation.mandate_id is None:
        # Verified token with no mandate linkage — nothing to settle against.
        return MandateCheckOutcome(
            allowed=False,
            status_code=403,
            deny_reason="biscuit_denied",
            message="Mandate token carries no mandate id",
            audit_metadata=meta,
        )
    return MandateCheckOutcome(allowed=True, audit_metadata=meta)


def draw_receipt(
    *,
    agent_id: str,
    endpoint: str,
    amount_cents: int,
    currency: str,
    settlement: bool,
    decision: str,
    presentation_metadata: dict,
    deny_reason: str | None = None,
    draw: dict | None = None,
    correlation_id: str | None = None,
) -> dict | None:
    """Assemble and sign the receipt handed back to the presenting agent.

    The return path of the delegation loop: the Biscuit carried authority
    down to this enforcement point; the receipt carries signed evidence of
    what was done — or refused — back up to whoever holds the token, so a
    delegator ends up with offline-verifiable proof of its delegate's
    actions. Denials get receipts too: "your delegate tried and was
    refused" is evidence the delegator wants.

    Signed with the same Ed25519 root key that anchors the tokens
    (common/biscuit/receipts.py). Best-effort by design: returns None if
    unsignable — a receipt failure must never block or fail the request
    it evidences.
    """
    from common.biscuit import mint_receipt

    payload: dict = {
        "kind": "mandate_draw_receipt",
        "agent_id": agent_id,
        "endpoint": endpoint,
        "amount_cents": amount_cents,
        "currency": currency,
        "settlement": settlement,
        "decision": decision,
    }
    if presentation_metadata.get("mandate_id"):
        payload["mandate_id"] = presentation_metadata["mandate_id"]
    if presentation_metadata.get("biscuit_revocation_id"):
        # Identifies WHICH copy of the authority acted — a parent's receipt
        # provably concerns its delegate's attenuated token.
        payload["revocation_id"] = presentation_metadata["biscuit_revocation_id"]
    if presentation_metadata.get("biscuit_block_count") is not None:
        payload["attenuation_blocks"] = presentation_metadata["biscuit_block_count"]
    if deny_reason:
        payload["deny_reason"] = deny_reason
    if presentation_metadata.get("biscuit_deny_detail"):
        payload["deny_detail"] = presentation_metadata["biscuit_deny_detail"]
    if draw:
        for src, dst in (
            ("spent_cents", "spent_cents"),
            ("limit_cents", "limit_cents"),
            ("remaining_cents", "remaining_cents"),
            ("exceeded", "exceeded"),
            ("status", "mandate_status"),
        ):
            if draw.get(src) is not None:
                payload[dst] = draw[src]
    if correlation_id:
        # Ties the receipt to the chained audit rows for this exact request —
        # a receipt-in-hand reconciles against the tamper-evident ledger.
        payload["correlation_id"] = correlation_id

    try:
        return mint_receipt(settings.biscuit_root_key_pem, payload)
    except ValueError as e:
        logger.warning("receipt not minted: %s", e)
        return None


def settle_draw(
    mandate_id: str,
    *,
    amount_cents: int,
    currency: str,
    settlement: bool,
    reference: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> MandateCheckOutcome:
    """Layer 2 — draw against the authoritative mandate (fail-closed).

    ``transport`` is a test seam (httpx.MockTransport); production callers
    leave it None.
    """
    if not mandate_circuit_breaker.can_execute():
        return MandateCheckOutcome(
            allowed=False,
            status_code=503,
            deny_reason="mandate_unavailable",
            message="Mandate service circuit breaker is open",
        )
    draw_token = settings.mandate_draw_token
    if not draw_token and settings.mandate_draw_token_file:
        try:
            with open(settings.mandate_draw_token_file) as fh:
                draw_token = fh.read().strip()
        except OSError as e:
            logger.warning("mandate_draw_token_file unreadable: %s", e)
    if not draw_token:
        return MandateCheckOutcome(
            allowed=False,
            status_code=503,
            deny_reason="mandate_unavailable",
            message="No mandate draw credential configured (MANDATE_DRAW_TOKEN[_FILE])",
        )

    body = {
        "amount_cents": amount_cents,
        "currency": currency,
        "settlement": settlement,
    }
    if reference:
        body["reference"] = reference

    try:
        with httpx.Client(
            base_url=settings.mandate_url,
            timeout=settings.mandate_check_timeout_ms / 1000.0,
            transport=transport,
        ) as client:
            resp = client.post(
                f"/api/v1/mandates/{mandate_id}/spend",
                json=body,
                headers={"Authorization": f"Bearer {draw_token}"},
            )
    except httpx.HTTPError as e:
        mandate_circuit_breaker.record_failure()
        logger.warning("Mandate draw unreachable for %s: %s — DENIED", mandate_id, e)
        return MandateCheckOutcome(
            allowed=False,
            status_code=503,
            deny_reason="mandate_unavailable",
            message="Mandate service unreachable — request denied (fail-closed)",
        )

    if resp.status_code >= 500:
        mandate_circuit_breaker.record_failure()
        return MandateCheckOutcome(
            allowed=False,
            status_code=503,
            deny_reason="mandate_unavailable",
            message=f"Mandate service error ({resp.status_code}) — request denied (fail-closed)",
        )

    mandate_circuit_breaker.record_success()

    if resp.status_code != 200:
        # 404 unknown mandate, 401/403 bad draw credential, …
        return MandateCheckOutcome(
            allowed=False,
            status_code=403,
            deny_reason="mandate_denied",
            message=f"Mandate draw rejected ({resp.status_code})",
            audit_metadata={"mandate_id": mandate_id},
        )

    draw = resp.json()
    meta = {
        "mandate_id": mandate_id,
        "spend_amount_cents": amount_cents,
        "spend_currency": currency,
        "spend_settlement": settlement,
        "mandate_spent_cents": draw.get("spent_cents"),
    }
    if draw.get("limit_cents") is not None:
        meta["mandate_limit_cents"] = draw["limit_cents"]
    if not draw.get("accepted"):
        meta["deny_reason"] = draw.get("deny_reason")
        return MandateCheckOutcome(
            allowed=False,
            status_code=403,
            deny_reason="mandate_denied",
            message=f"Mandate draw denied: {draw.get('deny_reason', 'unknown')}",
            audit_metadata=meta,
            draw=draw,
        )
    return MandateCheckOutcome(allowed=True, audit_metadata=meta, draw=draw)
