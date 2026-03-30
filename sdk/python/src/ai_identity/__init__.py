"""AI Identity Python SDK — identity, governance, and forensics for AI agents.

Quick start::

    from ai_identity import AIIdentityClient

    async with AIIdentityClient(api_key="aid_sk_...") as client:
        result = await client.agents.create(name="my-agent")
        print(result.api_key)  # Store this securely!
"""

from ai_identity.client import AIIdentityClient, SyncAIIdentityClient
from ai_identity.exceptions import (
    AIIdentityError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from ai_identity.models import (
    Agent,
    AgentCreate,
    AgentCreateResponse,
    AgentKey,
    AgentKeyCreateResponse,
    AgentKeyList,
    AgentKeyRotateResponse,
    AgentList,
    AgentUpdate,
    AuditChainVerification,
    AuditEntry,
    AuditList,
    AuditStats,
    Credential,
    CredentialCreate,
    CredentialCreateResponse,
    CredentialList,
    Policy,
    PolicyCreate,
)

__version__ = "0.1.0"

__all__ = [
    # Clients
    "AIIdentityClient",
    "SyncAIIdentityClient",
    # Exceptions
    "AIIdentityError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    # Models
    "Agent",
    "AgentCreate",
    "AgentCreateResponse",
    "AgentKey",
    "AgentKeyCreateResponse",
    "AgentKeyList",
    "AgentKeyRotateResponse",
    "AgentList",
    "AgentUpdate",
    "AuditChainVerification",
    "AuditEntry",
    "AuditList",
    "AuditStats",
    "Credential",
    "CredentialCreate",
    "CredentialCreateResponse",
    "CredentialList",
    "Policy",
    "PolicyCreate",
]
