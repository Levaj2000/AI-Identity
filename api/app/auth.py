"""MVP auth — X-API-Key header resolves to a user.

For MVP, the API key is a simple shared secret per user stored in the
users table. This will be replaced with proper agent key auth later.
The key is matched against users.email for simplicity (or a dedicated
api_key column when we add one). For now, we auto-create users on first
request to reduce friction during development.
"""

import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from common.models import User, get_db


async def get_current_user(
    x_api_key: str = Header(..., description="User API key for authentication"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve X-API-Key header to a User.

    MVP behavior: treat the key as a user identifier.
    If user doesn't exist, return 401.
    """
    if not x_api_key or len(x_api_key) < 8:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Look up user by API key — for MVP we store the key directly
    user = db.query(User).filter(User.email == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Defense-in-depth: set RLS session variable for PostgreSQL.
    # SET LOCAL is transaction-scoped — resets on commit/rollback.
    # FastAPI dependency caching ensures the same session is used by
    # both get_current_user and the route handler, so RLS will be active
    # for all queries in the request.
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "postgresql":
        db.execute(text("SET LOCAL app.current_user_id = :uid"), {"uid": str(user.id)})

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
