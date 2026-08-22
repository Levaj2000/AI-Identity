"""EdgeDeployment model — a registered off-platform enforcement point.

An edge deployment is a customer-resident gateway (Praxis/PPE with the
cpex-ocsf-audit plugin, or the hosted gateway itself) that streams signed
OCSF decision records into ``POST /api/v1/audit/ingest``. Registration
binds the deployment's chain identity (``chain_uid``) and signature
verification key to one organization, so an ingest credential can only
ever append to its own chains. See docs/specs/praxis-edge-enforcement.md.
"""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class EdgeStatus:
    """Edge deployment lifecycle states."""

    active = "active"
    revoked = "revoked"


class EdgeDeployment(Base):
    """A registered edge enforcement point and its ingest credential."""

    __tablename__ = "edge_deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # The emitter's configured chain identity. Unique across ALL orgs so a
    # stolen record from one tenant can never be replayed into another's
    # chain under the same identity.
    chain_uid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    authority_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ECDSA P-256 public key (PEM) the edge signs records with — validated
    # at registration. The matching private key never touches the platform.
    verify_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional JWKS kid the edge stamps at unmapped.signature_key_id; when
    # set, ingest rejects records claiming a different key id.
    key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Ingest credential — SHA-256 hashed, show-once (same pattern as AgentKey)
    ingest_key_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    ingest_key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EdgeStatus.active)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_ingest_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
