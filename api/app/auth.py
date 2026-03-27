"""Authentication — Clerk JWT verification + legacy X-API-Key fallback.

Primary auth: Clerk JWT tokens sent as Authorization: Bearer <token>.
The JWT is verified against Clerk's JWKS endpoint. The user is matched
by email from the JWT claims to the local users table.

Legacy fallback: X-API-Key header matched against users.email.
This will be removed once all clients migrate to Clerk auth.
"""

import logging
import uuid

import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from common.config.settings import settings
from common.models import User, get_db

logger = logging.getLogger("ai_identity.api.auth")

# ── Clerk JWKS cache ────────────────────────────────────────────────

_jwks_cache: dict | None = None
_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient | None:
    """Lazy-initialize the JWKS client for Clerk JWT verification."""
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client

    clerk_issuer = getattr(settings, "clerk_issuer", None)
    if not clerk_issuer:
        logger.warning("CLERK_ISSUER not set — Clerk JWT auth disabled")
        return None

    jwks_url = f"{clerk_issuer.rstrip('/')}/.well-known/jwks.json"
    _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)
    logger.info("Clerk JWKS client initialized: %s", jwks_url)
    return _jwks_client


def _verify_clerk_jwt(token: str) -> dict | None:
    """Verify a Clerk JWT and return the decoded claims, or None on failure."""
    client = _get_jwks_client()
    if not client:
        return None

    try:
        signing_key = client.get_signing_key_from_jwt(token)
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't set aud by default
        )
        return decoded
    except jwt.ExpiredSignatureError:
        logger.warning("Clerk JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Clerk JWT invalid: %s", e)
        return None
    except Exception as e:
        logger.warning("Clerk JWT verification failed: %s", e)
        return None


def _extract_email_from_clerk_claims(claims: dict) -> str | None:
    """Extract email from Clerk JWT claims.

    Clerk stores email in different places depending on session config:
    - claims.get("email") — if email is in the session token template
    - claims.get("email_addresses", [{}])[0].get("email_address")
    - claims.get("unsafe_metadata", {}).get("email")
    """
    # Direct email claim (most common with custom session token template)
    if claims.get("email"):
        return claims["email"]

    # Primary email address from Clerk's default claims
    email_addresses = claims.get("email_addresses", [])
    if email_addresses and isinstance(email_addresses, list):
        first = email_addresses[0]
        if isinstance(first, dict) and first.get("email_address"):
            return first["email_address"]
        if isinstance(first, str):
            return first

    # Fallback: check sub claim (Clerk user ID) — won't help for email lookup
    return None


# ── Main auth dependency ────────────────────────────────────────────


async def get_current_user(
    request: Request,
    x_api_key: str | None = Header(None, description="Legacy API key (email)"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from Clerk JWT or legacy X-API-Key.

    Auth priority:
    1. Authorization: Bearer <clerk-jwt> — verified against Clerk JWKS
    2. X-API-Key header — legacy email-as-key (will be removed)
    """
    user: User | None = None

    # ── Try Bearer token first (Clerk JWT) ──────────────────────
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        claims = _verify_clerk_jwt(token)
        if claims is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        email = _extract_email_from_clerk_claims(claims)
        clerk_user_id = claims.get("sub")

        if email:
            user = db.query(User).filter(User.email == email).first()

        # Auto-provision: if Clerk user exists but no local User, create one
        if user is None and email:
            user = User(
                id=uuid.uuid4(),
                email=email,
                role="owner",
                tier="free",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("Auto-provisioned user from Clerk: %s (clerk_id=%s)", email, clerk_user_id)

            # Send welcome email (fire-and-forget, never blocks auth)
            try:
                from sqlalchemy import func

                from api.app.email import send_welcome_email

                result = send_welcome_email(email)
                if result:
                    user.welcome_email_sent_at = func.now()
                    db.commit()
            except Exception:
                logger.warning(
                    "Welcome email failed for %s — user provisioned without email", email
                )

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Could not resolve user from token. Ensure email is included in Clerk session claims.",
            )

    # ── Fall back to legacy X-API-Key ───────────────────────────
    elif x_api_key and len(x_api_key) >= 8:
        user = db.query(User).filter(User.email == x_api_key).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Defense-in-depth: set RLS session variable for PostgreSQL
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "postgresql":
        db.execute(text("SET LOCAL app.current_user_id = :uid"), {"uid": str(user.id)})
        # Set org context for RLS (if user belongs to an org)
        if user.org_id:
            db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(user.org_id)})

    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have admin role.

    Returns 403 if the user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_org_role(*allowed_roles: str):
    """Dependency factory: require the user to have one of the specified org roles."""

    async def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.role == "admin":
            return user
        if not user.org_id:
            raise HTTPException(status_code=403, detail="No organization membership")
        from common.models.org_membership import OrgMembership

        membership = (
            db.query(OrgMembership)
            .filter(
                OrgMembership.org_id == user.org_id,
                OrgMembership.user_id == user.id,
            )
            .first()
        )
        if not membership or membership.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient organization role")
        return user

    return _check


def require_agent_role(*allowed_roles: str):
    """Dependency factory: require the user to have one of the specified agent roles.

    Fallbacks:
    - Agent creator (agent.user_id == user.id) always has 'owner' role
    - Org owner/admin has full access to org agents
    """

    async def _check(
        agent_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.role == "admin":
            return user
        from common.models import Agent
        from common.models.agent_assignment import AgentAssignment
        from common.models.org_membership import OrgMembership

        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Creator always has owner access
        if agent.user_id == user.id and (
            "owner" in allowed_roles or "operator" in allowed_roles or "viewer" in allowed_roles
        ):
            return user

        # Org admin/owner has full access to org agents
        if agent.org_id and user.org_id == agent.org_id:
            membership = (
                db.query(OrgMembership)
                .filter(
                    OrgMembership.org_id == user.org_id,
                    OrgMembership.user_id == user.id,
                )
                .first()
            )
            if membership and membership.role in ("owner", "admin"):
                return user

        # Check agent-level assignment
        assignment = (
            db.query(AgentAssignment)
            .filter(
                AgentAssignment.agent_id == agent_id,
                AgentAssignment.user_id == user.id,
            )
            .first()
        )
        if assignment and assignment.role in allowed_roles:
            return user

        raise HTTPException(status_code=403, detail="Insufficient agent access")

    return _check


def get_or_create_dev_user(db: Session, api_key: str) -> User:
    """Development helper — get or create a user for a given API key.

    Used by seed scripts and tests. NOT used in production routes.
    """
    user = db.query(User).filter(User.email == api_key).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=api_key,
            role="owner",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
