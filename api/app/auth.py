"""MVP auth — X-API-Key header resolves to a user.

For MVP, the API key is a simple shared secret per user stored in the
users table. This will be replaced with proper agent key auth later.
The key is matched against users.email for simplicity (or a dedicated
api_key column when we add one). For now, we auto-create users on first
request to reduce friction during development.
"""

import uuid

from fastapi import Depends, Header, HTTPException
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
