"""UpstreamCredential model — encrypted storage for upstream API provider keys.

SECURITY: The `encrypted_key` column stores ONLY Fernet ciphertext.
Plaintext upstream API keys are never persisted to disk or database.
Decryption occurs only in-memory, per-request, using CREDENTIAL_ENCRYPTION_KEY.
"""

import datetime
import enum
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class CredentialStatus(enum.StrEnum):
    """Upstream credential lifecycle status."""

    active = "active"
    rotated = "rotated"
    revoked = "revoked"


class UpstreamProvider(enum.StrEnum):
    """Known upstream LLM providers."""

    openai = "openai"
    anthropic = "anthropic"
    google = "google"
    azure_openai = "azure_openai"
    custom = "custom"


class UpstreamCredential(Base):
    """An encrypted upstream API credential scoped to an agent.

    The `encrypted_key` column stores only Fernet ciphertext — never plaintext.
    Decryption happens in-memory per-request using the CREDENTIAL_ENCRYPTION_KEY.
    """

    __tablename__ = "upstream_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider classification
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Encrypted storage — ONLY ciphertext
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)

    # Key prefix for identification (first 8 chars of original key, e.g. "sk-proj-")
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CredentialStatus.active.value
    )

    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(  # noqa: F821
        back_populates="upstream_credentials"
    )
