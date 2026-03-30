"""Credential models."""

from datetime import datetime

from pydantic import BaseModel, Field


class CredentialCreate(BaseModel):
    """Request body for storing an upstream credential."""

    provider: str = Field(..., description="Upstream provider: openai, anthropic, google, etc.")
    api_key: str = Field(..., description="Plaintext upstream API key — encrypted before storage")
    label: str | None = Field(None, description="Human-readable label")


class Credential(BaseModel):
    """Credential metadata. The encrypted key is never exposed."""

    id: int
    agent_id: str
    provider: str
    label: str | None = None
    key_prefix: str = Field(description="First 8 chars for identification")
    status: str = Field(description="active, rotated, or revoked")
    created_at: datetime
    updated_at: datetime


class CredentialCreateResponse(BaseModel):
    """Response for credential creation."""

    credential: Credential
    message: str = "Credential encrypted and stored successfully"


class CredentialList(BaseModel):
    """List of credentials."""

    items: list[Credential]
    total: int


class CredentialRotate(BaseModel):
    """Request body for rotating a credential's API key."""

    api_key: str = Field(..., description="New plaintext upstream API key")
