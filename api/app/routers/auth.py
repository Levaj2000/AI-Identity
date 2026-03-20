"""Auth endpoints — login validation and current user profile."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from common.models import User, get_db

logger = logging.getLogger("ai_identity.api.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Schemas ─────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Login request — email is the API key for MVP."""

    email: str


class UserProfile(BaseModel):
    """Current user profile returned by /me and /login."""

    id: str
    email: str
    role: str
    tier: str
    requests_this_month: int
    org_id: str | None = None

    model_config = {"from_attributes": True}


# ── Helpers ─────────────────────────────────────────────────────────


def _user_profile(user: User) -> UserProfile:
    return UserProfile(
        id=str(user.id),
        email=user.email,
        role=user.role,
        tier=user.tier,
        requests_this_month=user.requests_this_month,
        org_id=user.org_id,
    )


# ── Endpoints ───────────────────────────────────────────────────────


@router.get("/me", response_model=UserProfile, summary="Get current user profile")
def get_me(
    x_api_key: str = Header(..., description="User API key"),
    db: Session = Depends(get_db),
):
    """Validate API key and return the authenticated user's profile.

    Used by the dashboard to verify the stored API key is still valid
    and to load user info (role, tier, etc.) on page load.
    """
    if not x_api_key or len(x_api_key) < 8:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = db.query(User).filter(User.email == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return _user_profile(user)


@router.post("/login", response_model=UserProfile, summary="Validate credentials")
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Validate email (API key) and return user profile if valid.

    MVP auth: email serves as the API key. No password yet.
    Returns 401 if the email doesn't match any registered user.
    """
    email = body.email.strip().lower()

    if not email or len(email) < 8:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning("Login failed: unknown email %s", email[:3] + "***")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info("Login successful: user %s (%s)", user.id, user.role)
    return _user_profile(user)
