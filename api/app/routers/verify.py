"""Key verification endpoint — resolve a runtime API key to its parent agent.

Used by trusted external systems (e.g. the CEO Dashboard backend) that need to
authenticate inbound requests carrying per-agent runtime keys but cannot proxy
through the AI Identity gateway. The caller authenticates with their own admin
credentials; the request body contains the runtime key being verified.

Returns 200 with agent identity + metadata when the key is valid and active.
Returns 200 with ``valid=false`` and a structured ``reason`` when the key is
invalid, revoked, expired, or when the parent agent is suspended/revoked.

Plaintext keys are never logged. Each call records caller user_id, key prefix,
and decision for audit.
"""

import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.auth.keys import hash_key
from common.models import Agent, AgentKey, AgentStatus, KeyStatus, User, get_db

logger = logging.getLogger("ai_identity.api.verify")

router = APIRouter(prefix="/api/v1/keys", tags=["verify"])


class VerifyKeyRequest(BaseModel):
    key: str = Field(
        ...,
        description="The runtime API key to verify (e.g. aid_sk_...)",
        min_length=8,
    )


class VerifyKeyResponse(BaseModel):
    valid: bool
    agent_id: str | None = None
    agent_name: str | None = None
    metadata: dict[str, Any] | None = None
    agent_status: str | None = None
    key_type: str | None = None
    key_prefix: str | None = None
    reason: str | None = Field(
        None,
        description="Failure reason when valid=false. Stable enum: malformed_key, "
        "key_not_found, key_rotated, key_revoked, key_expired, agent_not_found, "
        "agent_suspended, agent_revoked.",
    )


@router.post(
    "/verify",
    response_model=VerifyKeyResponse,
    status_code=200,
    summary="Verify a runtime API key",
    response_description="Agent identity + metadata when valid; structured reason when not",
)
def verify_key(
    body: VerifyKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifyKeyResponse:
    """Resolve a runtime API key to its parent agent.

    Caller authenticates with their own admin credentials. The body carries
    the runtime key under verification. Plaintext keys are never logged or
    persisted by this endpoint.
    """
    plaintext = body.key

    if not plaintext.startswith(("aid_sk_", "aid_admin_")):
        logger.info("verify_key MALFORMED by user=%s", user.id)
        return VerifyKeyResponse(valid=False, reason="malformed_key")

    key_record = db.query(AgentKey).filter(AgentKey.key_hash == hash_key(plaintext)).first()

    if key_record is None:
        logger.info("verify_key MISS by user=%s prefix=%s", user.id, plaintext[:12])
        return VerifyKeyResponse(valid=False, reason="key_not_found")

    if key_record.status != KeyStatus.active.value:
        logger.info(
            "verify_key INACTIVE by user=%s key_id=%s status=%s",
            user.id,
            key_record.id,
            key_record.status,
        )
        return VerifyKeyResponse(valid=False, reason=f"key_{key_record.status}")

    if key_record.expires_at is not None:
        now = datetime.datetime.now(datetime.UTC)
        # Both sides timezone-aware
        expires_at = key_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.UTC)
        if expires_at < now:
            logger.info("verify_key EXPIRED by user=%s key_id=%s", user.id, key_record.id)
            return VerifyKeyResponse(valid=False, reason="key_expired")

    agent = db.query(Agent).filter(Agent.id == key_record.agent_id).first()
    if agent is None:
        return VerifyKeyResponse(valid=False, reason="agent_not_found")

    if agent.status != AgentStatus.active.value:
        logger.info(
            "verify_key AGENT_INACTIVE by user=%s agent_id=%s status=%s",
            user.id,
            agent.id,
            agent.status,
        )
        return VerifyKeyResponse(valid=False, reason=f"agent_{agent.status}")

    logger.info("verify_key OK by user=%s agent_id=%s", user.id, agent.id)
    return VerifyKeyResponse(
        valid=True,
        agent_id=str(agent.id),
        agent_name=agent.name,
        metadata=agent.metadata_,
        agent_status=agent.status,
        key_type=key_record.key_type,
        key_prefix=key_record.key_prefix,
    )
