"""Pydantic schemas for upstream credential CRUD operations.

SECURITY: CredentialResponse NEVER includes encrypted_key — the ciphertext
is an internal implementation detail that must not leak through the API.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Create ───────────────────────────────────────────────────────────────


class CredentialCreate(BaseModel):
    """Request body for storing a new upstream credential.

    The `api_key` field contains the plaintext upstream key — it is
    encrypted before storage and never persisted in plaintext.
    """

    provider: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Upstream provider: openai, anthropic, google, azure_openai, custom",
        examples=["openai"],
    )
    api_key: str = Field(
        ...,
        min_length=8,
        max_length=500,
        description="Plaintext upstream API key — encrypted before storage, never persisted",
        examples=["sk-proj-abc123def456"],
    )
    label: str | None = Field(
        None,
        max_length=255,
        description="Human-readable label for this credential",
        examples=["Production OpenAI Key"],
    )


# ── Response ─────────────────────────────────────────────────────────────


class CredentialResponse(BaseModel):
    """Upstream credential metadata. The encrypted key is NEVER exposed."""

    id: int = Field(description="Credential ID")
    agent_id: uuid.UUID = Field(description="Agent this credential belongs to")
    provider: str = Field(description="Upstream provider name")
    label: str | None = Field(description="Human-readable label")
    key_prefix: str = Field(
        description="First 8 chars of the upstream key for identification",
        examples=["sk-proj-"],
    )
    status: str = Field(
        description="Credential status: active, rotated, or revoked",
        examples=["active"],
    )
    created_at: datetime = Field(description="When the credential was stored")
    updated_at: datetime = Field(description="When the credential was last modified")

    model_config = {"from_attributes": True}


class CredentialCreateResponse(BaseModel):
    """Response for credential creation — confirms storage, no key echoed."""

    credential: CredentialResponse
    message: str = Field(
        default="Credential encrypted and stored successfully",
        description="Confirmation message",
    )


class CredentialListResponse(BaseModel):
    """List of upstream credentials with metadata (never the key)."""

    items: list[CredentialResponse] = Field(description="List of credentials")
    total: int = Field(description="Total number of credentials")


# ── Rotate / Revoke ──────────────────────────────────────────────────────


class CredentialRotateRequest(BaseModel):
    """Request body for rotating an upstream credential's API key."""

    api_key: str = Field(
        ...,
        min_length=8,
        max_length=500,
        description="New plaintext upstream API key to replace the current one",
    )


# ── Master Key Rotation ─────────────────────────────────────────────────


class MasterKeyRotateRequest(BaseModel):
    """Request body for re-encrypting all credentials with a new master key."""

    new_master_key: str = Field(
        ...,
        min_length=32,
        description="New Fernet master key to rotate to",
    )


class MasterKeyRotateResponse(BaseModel):
    """Response for master key rotation."""

    credentials_re_encrypted: int = Field(description="Number of credentials re-encrypted")
    message: str = Field(description="Human-readable result")
