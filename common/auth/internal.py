"""HMAC-SHA256 internal service authentication.

Provides mutual authentication between the API and Gateway services.
Uses a shared secret (INTERNAL_SERVICE_KEY env var) to sign and verify
requests via X-Internal-Signature and X-Internal-Timestamp headers.

Security properties:
  - Replay protection: requests older than 30 seconds are rejected
  - Tamper detection: HMAC covers method + path + body hash + timestamp
  - Fail-closed: empty/missing key rejects all requests
  - Constant-time comparison: hmac.compare_digest prevents timing attacks

Canonical request format (newline-separated, like AWS SigV4):
  HMAC-SHA256(timestamp + "\\n" + METHOD + "\\n" + path + "\\n" + SHA256(body),
              key=INTERNAL_SERVICE_KEY)

Phase 2 will add mTLS on top of this.
"""

import hashlib
import hmac
import logging
import time

from fastapi import HTTPException, Request

from common.config.settings import settings

logger = logging.getLogger("ai_identity.internal_auth")

# ── Constants ────────────────────────────────────────────────────────────

HEADER_SIGNATURE = "X-Internal-Signature"
HEADER_TIMESTAMP = "X-Internal-Timestamp"
REPLAY_WINDOW_SECONDS = 30


# ── Request Signing (Client Side) ────────────────────────────────────────


def sign_request(
    method: str,
    path: str,
    body: bytes | None = None,
    key: str | None = None,
    timestamp: float | None = None,
) -> dict[str, str]:
    """Sign an outgoing internal request.

    Args:
        method: HTTP method (GET, POST, etc.) — uppercased internally.
        path: Request path (e.g., "/api/v1/agents/lookup").
        body: Raw request body bytes. None or empty for GET requests.
        key: HMAC key override (for testing). Defaults to settings.internal_service_key.
        timestamp: Unix epoch override (for testing). Defaults to time.time().

    Returns:
        Dict with X-Internal-Timestamp and X-Internal-Signature headers.
        Caller should merge these into the request headers.

    Raises:
        ValueError: If the key is empty (fail-closed).
    """
    signing_key = key if key is not None else settings.internal_service_key
    if not signing_key:
        msg = "INTERNAL_SERVICE_KEY is not configured — cannot sign request"
        raise ValueError(msg)

    ts = str(int(timestamp or time.time()))
    body_hash = hashlib.sha256(body or b"").hexdigest()
    canonical = f"{ts}\n{method.upper()}\n{path}\n{body_hash}"

    signature = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        HEADER_TIMESTAMP: ts,
        HEADER_SIGNATURE: signature,
    }


# ── Request Verification (Server Side) ───────────────────────────────────


def verify_request(
    method: str,
    path: str,
    body: bytes | None,
    signature: str,
    timestamp_str: str,
    key: str | None = None,
) -> bool:
    """Verify an incoming internal request's HMAC signature.

    Args:
        method: HTTP method.
        path: Request path.
        body: Raw request body bytes.
        signature: Value of X-Internal-Signature header.
        timestamp_str: Value of X-Internal-Timestamp header.
        key: HMAC key override (for testing). Defaults to settings.internal_service_key.

    Returns:
        True if the signature is valid AND the timestamp is within the
        replay window. False otherwise (fail-closed).
    """
    signing_key = key if key is not None else settings.internal_service_key

    # Fail-closed: empty key rejects everything
    if not signing_key:
        logger.warning("Internal auth rejected: INTERNAL_SERVICE_KEY is not configured")
        return False

    # Validate timestamp format
    try:
        ts = int(timestamp_str)
    except (ValueError, TypeError):
        logger.warning("Internal auth rejected: invalid timestamp format")
        return False

    # Replay protection: reject requests outside the ±30 second window
    now = int(time.time())
    if abs(now - ts) > REPLAY_WINDOW_SECONDS:
        logger.warning(
            "Internal auth rejected: timestamp %d is %ds from now (%d)",
            ts,
            abs(now - ts),
            now,
        )
        return False

    # Recompute the expected signature
    body_hash = hashlib.sha256(body or b"").hexdigest()
    canonical = f"{timestamp_str}\n{method.upper()}\n{path}\n{body_hash}"

    expected = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)


# ── FastAPI Dependency ───────────────────────────────────────────────────


async def require_internal_auth(request: Request) -> None:
    """FastAPI dependency that verifies internal service authentication.

    Usage as route dependency:
        @router.get("/internal/x", dependencies=[Depends(require_internal_auth)])
        async def my_internal_endpoint(): ...

    Or as a parameter dependency:
        async def my_endpoint(
            _auth: None = Depends(require_internal_auth),
            db: Session = Depends(get_db),
        ): ...

    Raises:
        HTTPException(401): If signature is missing, invalid, expired,
            or INTERNAL_SERVICE_KEY is not configured.
    """
    signature = request.headers.get(HEADER_SIGNATURE)
    timestamp = request.headers.get(HEADER_TIMESTAMP)

    if not signature or not timestamp:
        logger.warning(
            "Internal auth rejected: missing headers on %s %s",
            request.method,
            request.url.path,
        )
        raise HTTPException(
            status_code=401,
            detail="Missing internal authentication headers",
        )

    # Read the body — FastAPI caches it after first read
    body = await request.body()

    if not verify_request(
        method=request.method,
        path=request.url.path,
        body=body,
        signature=signature,
        timestamp_str=timestamp,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid internal authentication",
        )
