"""Developer authentication for the Mandate Service.

Accepts the same credentials as the main API:
  1. Authorization: Bearer <clerk-jwt>  (primary)
  2. X-API-Key: <email>               (legacy fallback)

User must already exist in the users table — no auto-provisioning here.
"""

import logging

import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from common.config.settings import settings
from common.models import User, get_db

logger = logging.getLogger("ai_identity.mandate.auth")

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient | None:
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client

    clerk_issuer = getattr(settings, "clerk_issuer", None)
    if not clerk_issuer:
        logger.warning("CLERK_ISSUER not set — Clerk JWT auth disabled")
        return None

    jwks_url = f"{clerk_issuer.rstrip('/')}/.well-known/jwks.json"
    _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def _verify_clerk_jwt(token: str) -> dict | None:
    client = _get_jwks_client()
    if not client:
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Clerk JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Clerk JWT invalid: %s", e)
        return None


def _email_from_claims(claims: dict) -> str | None:
    if claims.get("email"):
        return claims["email"]
    for ea in claims.get("email_addresses", []):
        if isinstance(ea, dict) and ea.get("email_address"):
            return ea["email_address"]
        if isinstance(ea, str):
            return ea
    return None


async def get_current_user(
    request: Request,
    x_api_key: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    user: User | None = None

    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        claims = _verify_clerk_jwt(auth_header[7:])
        if claims is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        email = _email_from_claims(claims)
        if email:
            user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(
                status_code=401, detail="User not found — sign in via the main API first"
            )

    elif x_api_key and len(x_api_key) >= 8:
        user = db.query(User).filter(User.email == x_api_key).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")

    return user
