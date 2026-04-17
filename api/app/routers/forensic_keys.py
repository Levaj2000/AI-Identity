"""Public JWKS endpoint for forensic attestation verification keys.

``GET /.well-known/ai-identity-public-keys.json`` publishes the public
half of every signing key version so third-party verifiers can resolve
``AttestationPayloadV1.signer_key_id`` → public key without trusting
AI Identity operationally. See ``docs/forensics/attestation-format.md``.

Public by design — no auth. The document is safe to cache at the CDN
layer; rotation is operator-triggered and infrequent, so a 1-hour TTL
is a reasonable default.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from common.forensic import build_jwks

router = APIRouter(tags=["forensics.keys"])


@router.get(
    "/.well-known/ai-identity-public-keys.json",
    summary="JWKS for forensic attestation verification keys",
    response_description=(
        "JSON Web Key Set (RFC 7517) of ECDSA P-256 public keys. Each "
        "entry's `kid` matches the `signer_key_id` on a DSSE envelope."
    ),
)
def get_forensic_jwks() -> JSONResponse:
    """Return the JWKS document.

    Cache-Control allows the CDN to hold the document for an hour. KMS
    key rotations are operator-triggered and rare — a brief staleness
    window after rotation is acceptable; the old key versions remain
    published so any attestations signed during that window still
    verify.
    """
    jwks = build_jwks()
    return JSONResponse(
        content=jwks,
        headers={
            # Public, safe to cache. Rotation is operator-triggered and
            # old versions stay in the document, so staleness isn't a
            # verifiability hazard.
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "application/jwk-set+json",
        },
    )
