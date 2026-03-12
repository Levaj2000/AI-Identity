"""Agent Key management endpoints — create, list, revoke, rotate."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.auth.keys import generate_api_key, get_key_prefix, hash_key
from common.models import AgentKey, AgentStatus, KeyStatus, KeyType, User, get_db
from common.queries import get_user_agent
from common.schemas.agent import (
    AgentKeyCreateResponse,
    AgentKeyListResponse,
    AgentKeyResponse,
    AgentKeyRotateResponse,
)

logger = logging.getLogger("ai_identity.api.keys")

router = APIRouter(prefix="/api/v1/agents/{agent_id}/keys", tags=["keys"])

# Grace period for rotated keys (hours)
ROTATION_GRACE_HOURS = 24


# ── Helpers ──────────────────────────────────────────────────────────────


def _revoke_expired_keys(db: Session, agent_id: uuid.UUID) -> int:
    """Revoke any rotated keys past their expiry. Returns count of revoked keys."""
    now = datetime.now(UTC)
    count = (
        db.query(AgentKey)
        .filter(
            AgentKey.agent_id == agent_id,
            AgentKey.status == KeyStatus.rotated.value,
            AgentKey.expires_at <= now,
        )
        .update({"status": KeyStatus.revoked.value}, synchronize_session="fetch")
    )
    if count:
        db.commit()
        logger.info("Auto-revoked %d expired key(s) for agent %s", count, agent_id)
    return count


# ── POST /api/v1/agents/{agent_id}/keys ──────────────────────────────────


@router.post(
    "",
    response_model=AgentKeyCreateResponse,
    status_code=201,
    summary="Create key",
    response_description="The new key metadata with show-once plaintext key",
    responses={
        400: {"description": "Cannot issue key for a revoked agent"},
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def create_key(
    agent_id: uuid.UUID,
    key_type: str = Query(
        "runtime",
        pattern="^(runtime|admin)$",
        description="Key type: runtime (aid_sk_) for proxy endpoints, admin (aid_admin_) for management",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new API key for an agent.

    **Key types:**
    - `runtime` (default) — Prefix `aid_sk_`. For proxy/runtime endpoints only.
      The gateway will reject this key on management endpoints (403).
    - `admin` — Prefix `aid_admin_`. For identity/policy management API only.
      The gateway will reject this key on proxy endpoints (403).

    The response includes the plaintext key — **store it immediately**, it is
    only shown once.

    Cannot issue keys for revoked agents.
    """
    agent = get_user_agent(db, user, agent_id)

    if agent.status == AgentStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Cannot issue key for a revoked agent")

    # Clean up expired rotated keys
    _revoke_expired_keys(db, agent.id)

    # Generate and store the key with the correct prefix for its type
    plaintext_key = generate_api_key(key_type=key_type)
    agent_key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        key_type=key_type,
        status=KeyStatus.active.value,
    )
    db.add(agent_key)
    db.commit()
    db.refresh(agent_key)

    logger.info("Key created for agent %s (key_id=%d)", agent.id, agent_key.id)

    return AgentKeyCreateResponse(
        key=_key_to_response(agent_key),
        api_key=plaintext_key,
    )


# ── GET /api/v1/agents/{agent_id}/keys ───────────────────────────────────


@router.get(
    "",
    response_model=AgentKeyListResponse,
    summary="List keys",
    response_description="List of keys with prefix and status (never the full key or hash)",
    responses={
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def list_keys(
    agent_id: uuid.UUID,
    status: str | None = Query(
        None,
        pattern="^(active|rotated|revoked)$",
        description="Filter by key status: active, rotated, or revoked",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all keys for an agent.

    Returns key prefix and status for each key — the full key and hash
    are never exposed. Expired rotated keys are automatically revoked
    before results are returned.

    Use `?status=active` to see only active keys.
    """
    agent = get_user_agent(db, user, agent_id)

    # Clean up expired rotated keys before listing
    _revoke_expired_keys(db, agent.id)

    query = db.query(AgentKey).filter(AgentKey.agent_id == agent.id)

    if status:
        query = query.filter(AgentKey.status == status)

    total = query.count()
    keys = query.order_by(AgentKey.created_at.desc()).all()

    return AgentKeyListResponse(
        items=[_key_to_response(k) for k in keys],
        total=total,
    )


# ── POST /api/v1/agents/{agent_id}/keys/rotate ──────────────────────────


@router.post(
    "/rotate",
    response_model=AgentKeyRotateResponse,
    status_code=201,
    summary="Rotate key",
    response_description="New active key + old key with 24hr grace period",
    responses={
        400: {"description": "Cannot rotate: agent is revoked or has no active keys"},
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def rotate_key(
    agent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rotate the oldest active key: issue a new key and set the old one to rotated.

    The old key enters a **24-hour grace period** (`status=rotated`, `expires_at`
    set to now + 24h). During this window both old and new keys are valid,
    giving you time to update your configuration. After the grace period,
    the old key is automatically revoked on the next API call.

    The response includes the new plaintext key — **store it immediately**.
    """
    agent = get_user_agent(db, user, agent_id)

    if agent.status == AgentStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Cannot rotate key for a revoked agent")

    # Clean up any already-expired rotated keys
    _revoke_expired_keys(db, agent.id)

    # Find the oldest active key
    old_key = (
        db.query(AgentKey)
        .filter(
            AgentKey.agent_id == agent.id,
            AgentKey.status == KeyStatus.active.value,
        )
        .order_by(AgentKey.created_at.asc())
        .first()
    )
    if not old_key:
        raise HTTPException(status_code=400, detail="No active key to rotate")

    # Rotate: old key → rotated with grace period
    old_key.status = KeyStatus.rotated.value
    old_key.expires_at = datetime.now(UTC) + timedelta(hours=ROTATION_GRACE_HOURS)

    # Generate the new key — preserves the same key_type as the rotated key
    inherited_type = old_key.key_type if old_key.key_type else KeyType.runtime.value
    plaintext_key = generate_api_key(key_type=inherited_type)
    new_key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        key_type=inherited_type,
        status=KeyStatus.active.value,
    )
    db.add(new_key)
    db.commit()
    db.refresh(old_key)
    db.refresh(new_key)

    logger.info(
        "Key rotated for agent %s: old_key=%d → rotated (expires %s), new_key=%d",
        agent.id,
        old_key.id,
        old_key.expires_at,
        new_key.id,
    )

    return AgentKeyRotateResponse(
        new_key=_key_to_response(new_key),
        api_key=plaintext_key,
        rotated_key=_key_to_response(old_key),
    )


# ── DELETE /api/v1/agents/{agent_id}/keys/{key_id} ──────────────────────


@router.delete(
    "/{key_id}",
    response_model=AgentKeyResponse,
    summary="Revoke key",
    response_description="The revoked key",
    responses={
        400: {"description": "Key is already revoked"},
        404: {"description": "Agent or key not found"},
    },
)
def revoke_key(
    agent_id: uuid.UUID,
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific API key for an agent.

    The key is immediately invalidated and cannot be used for authentication.
    The key record is preserved with `status=revoked` for audit purposes.
    This action cannot be undone — issue a new key if needed.
    """
    agent = get_user_agent(db, user, agent_id)

    key = db.query(AgentKey).filter(AgentKey.id == key_id, AgentKey.agent_id == agent.id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    if key.status == KeyStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Key is already revoked")

    key.status = KeyStatus.revoked.value
    db.commit()
    db.refresh(key)

    logger.info("Key revoked: key_id=%d for agent %s", key.id, agent.id)
    return _key_to_response(key)


# ── Response Helper ──────────────────────────────────────────────────────


def _key_to_response(key: AgentKey) -> AgentKeyResponse:
    """Convert an AgentKey model to response schema."""
    return AgentKeyResponse(
        id=key.id,
        agent_id=key.agent_id,
        key_prefix=key.key_prefix,
        key_type=key.key_type if key.key_type else "runtime",
        status=key.status,
        expires_at=key.expires_at,
        created_at=key.created_at,
    )
