"""Upstream Credential management — store, list, revoke, rotate encrypted credentials.

SECURITY: Upstream API keys are Fernet-encrypted before storage.
The `encrypted_key` column contains only ciphertext. Plaintext keys
are held only in memory during the encrypt/decrypt operation and are
never logged, returned in responses, or persisted to disk.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.config.settings import settings
from common.crypto.exceptions import DecryptionError, EncryptionError
from common.crypto.fernet import encrypt_credential, re_encrypt_credential, validate_master_key
from common.models import CredentialStatus, UpstreamCredential, User, get_db
from common.queries import get_user_agent
from common.schemas.credential import (
    CredentialCreate,
    CredentialCreateResponse,
    CredentialListResponse,
    CredentialResponse,
    CredentialRotateRequest,
    MasterKeyRotateRequest,
    MasterKeyRotateResponse,
)

logger = logging.getLogger("ai_identity.api.credentials")

router = APIRouter(
    prefix="/api/v1/agents/{agent_id}/credentials",
    tags=["credentials"],
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _credential_to_response(cred: UpstreamCredential) -> CredentialResponse:
    """Convert model to response schema — never exposes encrypted_key."""
    return CredentialResponse(
        id=cred.id,
        agent_id=cred.agent_id,
        provider=cred.provider,
        label=cred.label,
        key_prefix=cred.key_prefix,
        status=cred.status,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )


# ── POST /api/v1/agents/{agent_id}/credentials ──────────────────────────


@router.post(
    "",
    response_model=CredentialCreateResponse,
    status_code=201,
    summary="Store encrypted credential",
    response_description="Credential metadata (plaintext key is never echoed)",
    responses={
        404: {"description": "Agent not found or belongs to another user"},
        500: {"description": "Encryption key not configured"},
    },
)
def create_credential(
    agent_id: uuid.UUID,
    body: CredentialCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store a new upstream API credential, encrypted at rest.

    The plaintext `api_key` is Fernet-encrypted before storage and is
    **never persisted or returned**. Only the `key_prefix` (first 8 chars)
    is stored alongside the ciphertext for identification purposes.
    """
    agent = get_user_agent(db, user, agent_id)

    try:
        encrypted = encrypt_credential(body.api_key, settings.credential_encryption_key)
    except EncryptionError as e:
        logger.error("Encryption failed for agent %s: %s", agent.id, type(e).__name__)
        raise HTTPException(
            status_code=500,
            detail="Credential encryption is not configured. Contact your administrator.",
        ) from e

    credential = UpstreamCredential(
        agent_id=agent.id,
        provider=body.provider,
        label=body.label,
        encrypted_key=encrypted,
        key_prefix=body.api_key[:8],
        status=CredentialStatus.active.value,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    logger.info(
        "Credential stored for agent %s (credential_id=%d, provider=%s)",
        agent.id,
        credential.id,
        credential.provider,
    )

    return CredentialCreateResponse(credential=_credential_to_response(credential))


# ── GET /api/v1/agents/{agent_id}/credentials ────────────────────────────


@router.get(
    "",
    response_model=CredentialListResponse,
    summary="List credentials",
    response_description="Credential metadata (never ciphertext)",
    responses={
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def list_credentials(
    agent_id: uuid.UUID,
    status: str | None = Query(
        None,
        pattern="^(active|rotated|revoked)$",
        description="Filter by credential status",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all upstream credentials for an agent (metadata only).

    The encrypted key is **never** included in the response.
    Use `?status=active` to filter by lifecycle status.
    """
    agent = get_user_agent(db, user, agent_id)

    query = db.query(UpstreamCredential).filter(
        UpstreamCredential.agent_id == agent.id,
    )
    if status:
        query = query.filter(UpstreamCredential.status == status)

    total = query.count()
    credentials = query.order_by(UpstreamCredential.created_at.desc()).all()

    return CredentialListResponse(
        items=[_credential_to_response(c) for c in credentials],
        total=total,
    )


# ── GET /api/v1/agents/{agent_id}/credentials/{credential_id} ───────────


@router.get(
    "/{credential_id}",
    response_model=CredentialResponse,
    summary="Get credential",
    response_description="Single credential metadata",
    responses={
        404: {"description": "Credential or agent not found"},
    },
)
def get_credential(
    agent_id: uuid.UUID,
    credential_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single upstream credential's metadata by ID."""
    agent = get_user_agent(db, user, agent_id)

    cred = (
        db.query(UpstreamCredential)
        .filter(
            UpstreamCredential.id == credential_id,
            UpstreamCredential.agent_id == agent.id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    return _credential_to_response(cred)


# ── PUT /api/v1/agents/{agent_id}/credentials/{credential_id}/rotate ────


@router.put(
    "/{credential_id}/rotate",
    response_model=CredentialResponse,
    summary="Rotate upstream key",
    response_description="Updated credential metadata",
    responses={
        400: {"description": "Cannot rotate a revoked credential"},
        404: {"description": "Credential or agent not found"},
        500: {"description": "Encryption key not configured"},
    },
)
def rotate_credential(
    agent_id: uuid.UUID,
    credential_id: int,
    body: CredentialRotateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Replace the upstream API key for an existing credential.

    The old ciphertext is overwritten with the new encrypted key.
    The `key_prefix` is updated to reflect the new key.
    """
    agent = get_user_agent(db, user, agent_id)

    cred = (
        db.query(UpstreamCredential)
        .filter(
            UpstreamCredential.id == credential_id,
            UpstreamCredential.agent_id == agent.id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    if cred.status == CredentialStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Cannot rotate a revoked credential")

    try:
        encrypted = encrypt_credential(body.api_key, settings.credential_encryption_key)
    except EncryptionError as e:
        logger.error("Encryption failed during rotation: %s", type(e).__name__)
        raise HTTPException(
            status_code=500,
            detail="Credential encryption is not configured. Contact your administrator.",
        ) from e

    cred.encrypted_key = encrypted
    cred.key_prefix = body.api_key[:8]
    db.commit()
    db.refresh(cred)

    logger.info("Credential rotated: credential_id=%d for agent %s", cred.id, agent.id)
    return _credential_to_response(cred)


# ── DELETE /api/v1/agents/{agent_id}/credentials/{credential_id} ────────


@router.delete(
    "/{credential_id}",
    response_model=CredentialResponse,
    summary="Revoke credential",
    response_description="The revoked credential",
    responses={
        400: {"description": "Credential is already revoked"},
        404: {"description": "Credential or agent not found"},
    },
)
def revoke_credential(
    agent_id: uuid.UUID,
    credential_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke an upstream credential.

    The credential is marked as revoked and can no longer be used
    for upstream API requests. The record is preserved for audit purposes.
    """
    agent = get_user_agent(db, user, agent_id)

    cred = (
        db.query(UpstreamCredential)
        .filter(
            UpstreamCredential.id == credential_id,
            UpstreamCredential.agent_id == agent.id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    if cred.status == CredentialStatus.revoked.value:
        raise HTTPException(status_code=400, detail="Credential is already revoked")

    cred.status = CredentialStatus.revoked.value
    db.commit()
    db.refresh(cred)

    logger.info("Credential revoked: credential_id=%d for agent %s", cred.id, agent.id)
    return _credential_to_response(cred)


# ── POST /api/v1/agents/{agent_id}/credentials/rotate-master-key ────────


@router.post(
    "/rotate-master-key",
    response_model=MasterKeyRotateResponse,
    summary="Rotate master encryption key",
    response_description="Count of re-encrypted credentials",
    responses={
        400: {"description": "Invalid new master key"},
        404: {"description": "Agent not found or belongs to another user"},
    },
)
def rotate_master_key(
    agent_id: uuid.UUID,
    body: MasterKeyRotateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-encrypt all active credentials for this agent with a new master key.

    This is used when rotating the `CREDENTIAL_ENCRYPTION_KEY` env var.
    All active credentials are decrypted with the current key and re-encrypted
    with the new key in a single transaction.

    After this succeeds, update `CREDENTIAL_ENCRYPTION_KEY` to the new key.
    """
    agent = get_user_agent(db, user, agent_id)

    # Validate the new key before starting
    try:
        validate_master_key(body.new_master_key)
    except EncryptionError as e:
        raise HTTPException(status_code=400, detail="Invalid Fernet master key format") from e

    credentials = (
        db.query(UpstreamCredential)
        .filter(
            UpstreamCredential.agent_id == agent.id,
            UpstreamCredential.status == CredentialStatus.active.value,
        )
        .all()
    )

    count = 0
    try:
        for cred in credentials:
            cred.encrypted_key = re_encrypt_credential(
                cred.encrypted_key,
                settings.credential_encryption_key,
                body.new_master_key,
            )
            count += 1
        db.commit()
    except DecryptionError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to re-encrypt credentials — current master key may be wrong",
        ) from e

    logger.info(
        "Master key rotated for agent %s: %d credential(s) re-encrypted",
        agent.id,
        count,
    )

    return MasterKeyRotateResponse(
        credentials_re_encrypted=count,
        message=f"Successfully re-encrypted {count} credential(s). "
        "Update CREDENTIAL_ENCRYPTION_KEY to the new key.",
    )
