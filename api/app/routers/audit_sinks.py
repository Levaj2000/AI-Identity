"""Audit forwarding sink management — CRUD + test delivery.

All endpoints are scoped to the caller's current organization. Creating,
updating, or deleting a sink requires ``owner`` or ``admin`` role in the
org — audit-feed routing is a security-critical configuration.

Every lifecycle event (create / update / delete / test) generates its own
audit row via ``create_audit_entry`` so nobody can silently reconfigure
where a customer's audit feed flows.
"""

from __future__ import annotations

import logging
import secrets
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from api.app.auth import get_current_user
from common.audit import create_audit_entry
from common.audit.transports import TRANSPORTS
from common.models import (
    AuditLogOutbox,
    AuditLogSink,
    OrgMembership,
    OutboxStatus,
    User,
    get_db,
)
from common.schemas.audit_sink import (
    SinkCreate,
    SinkCreatedResponse,
    SinkListResponse,
    SinkResponse,
    SinkTestResponse,
    SinkUpdate,
)

logger = logging.getLogger("ai_identity.api.audit_sinks")

router = APIRouter(prefix="/api/v1/audit/sinks", tags=["audit", "sinks"])


# ── Helpers ─────────────────────────────────────────────────────────


def _require_org_admin(db: Session, user: User) -> uuid.UUID:
    """Return the caller's org_id only if they are owner/admin in it.

    403 for any other state — including no org membership at all. Sinks
    are an enterprise-facing feature; personal-workspace users don't need
    them and don't get access to the endpoint.
    """
    if user.role == "admin" and user.org_id:
        return user.org_id
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="Audit sink management requires an organization membership",
        )
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == user.org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.role.in_(("owner", "admin")),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="Owner or admin role in the organization is required",
        )
    return user.org_id


def _get_sink_scoped(db: Session, sink_id: uuid.UUID, org_id: uuid.UUID) -> AuditLogSink:
    """Load a sink and 404 if it doesn't belong to the caller's org.

    Intentionally returns 404 (not 403) for cross-org access to avoid leaking
    sink existence to non-members.
    """
    sink = (
        db.query(AuditLogSink)
        .filter(
            AuditLogSink.id == sink_id,
            AuditLogSink.org_id == org_id,
            AuditLogSink.deleted_at.is_(None),
        )
        .first()
    )
    if sink is None:
        raise HTTPException(status_code=404, detail="Sink not found")
    return sink


def _generate_secret() -> str:
    """Fresh HMAC signing secret — 64 hex chars (32 bytes of entropy)."""
    return secrets.token_hex(32)


def _audit_sink_lifecycle(
    db: Session,
    *,
    user: User,
    sink: AuditLogSink,
    action: str,
) -> None:
    """Log a meta-audit row for a sink lifecycle event.

    ``action`` is one of: sink_created, sink_updated, sink_deleted,
    sink_tested, sink_secret_rotated. We attach the lifecycle event to an
    existing agent in the org if one exists, or fall back to the org-level
    sentinel handling in the writer. This avoids a hard dependency on the
    agent having a specific role for meta-audit events.
    """
    # Find any agent in the org for the audit row's agent_id anchor —
    # the existing audit_log schema requires agent_id NOT NULL, and
    # sink events are org-level, not agent-level. Using the first agent
    # is a pragmatic compromise for MVP. A future schema revision could
    # make agent_id nullable for org-level events (tracked in #136).
    from common.models import Agent

    agent = (
        db.query(Agent).filter(Agent.user_id == user.id).order_by(Agent.created_at.asc()).first()
    )
    if agent is None:
        # No agent yet; writer's sentinel-org fallback will accept this
        # too, but we need some agent_id. Skip meta-audit for pre-agent
        # flows — creating a sink before any agent exists is rare.
        logger.info("skipping %s meta-audit for user %s (no agent yet)", action, user.id)
        return

    create_audit_entry(
        db,
        agent_id=agent.id,
        endpoint=f"/api/v1/audit/sinks/{sink.id}",
        method="POST",
        decision="allow",
        request_metadata={
            "action_type": action,
            "resource_type": "audit_sink",
        },
        user_id=user.id,
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=SinkCreatedResponse,
    status_code=201,
    summary="Create a new audit-forwarding sink",
    response_description="The new sink, including the one-time secret",
)
def create_sink(
    body: SinkCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SinkCreatedResponse:
    """Register a new sink for the caller's organization.

    The returned ``secret`` is the HMAC signing key for webhook deliveries.
    Store it in your webhook receiver — AI Identity will not show it again.
    If omitted in the request, we generate one.
    """
    org_id = _require_org_admin(db, user)
    secret = body.secret or _generate_secret()

    sink = AuditLogSink(
        org_id=org_id,
        name=body.name,
        kind=body.kind,
        url=body.url,
        secret=secret,
        description=body.description,
        filter_config=body.filter.model_dump(exclude_none=True),
        created_by=user.id,
    )
    db.add(sink)
    db.commit()
    db.refresh(sink)

    _audit_sink_lifecycle(db, user=user, sink=sink, action="sink_created")

    return SinkCreatedResponse(
        id=sink.id,
        org_id=sink.org_id,
        name=sink.name,
        kind=sink.kind,
        url=sink.url,
        description=sink.description,
        enabled=sink.enabled,
        filter=sink.filter_config,
        consecutive_failures=sink.consecutive_failures,
        circuit_opened_at=sink.circuit_opened_at,
        created_at=sink.created_at,
        updated_at=sink.updated_at,
        created_by=sink.created_by,
        secret=secret,
    )


@router.get(
    "",
    response_model=SinkListResponse,
    summary="List audit-forwarding sinks for the caller's org",
)
def list_sinks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SinkListResponse:
    org_id = _require_org_admin(db, user)
    rows = (
        db.query(AuditLogSink)
        .filter(
            AuditLogSink.org_id == org_id,
            AuditLogSink.deleted_at.is_(None),
        )
        .order_by(AuditLogSink.created_at.desc())
        .all()
    )
    items = [
        SinkResponse(
            id=s.id,
            org_id=s.org_id,
            name=s.name,
            kind=s.kind,
            url=s.url,
            description=s.description,
            enabled=s.enabled,
            filter=s.filter_config or {},
            consecutive_failures=s.consecutive_failures,
            circuit_opened_at=s.circuit_opened_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
            created_by=s.created_by,
        )
        for s in rows
    ]
    return SinkListResponse(items=items, total=len(items))


@router.patch(
    "/{sink_id}",
    response_model=SinkCreatedResponse,
    summary="Update a sink (or rotate its secret)",
)
def update_sink(
    sink_id: uuid.UUID,
    body: SinkUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SinkCreatedResponse:
    """Apply a partial update. If ``rotate_secret=true``, generate and return
    a new secret — the response is the only time the new secret is shown.

    If nothing is rotated, the ``secret`` field is echoed as an empty string
    to keep the response shape consistent.
    """
    org_id = _require_org_admin(db, user)
    sink = _get_sink_scoped(db, sink_id, org_id)

    if body.name is not None:
        sink.name = body.name
    if body.url is not None:
        sink.url = body.url
    if body.description is not None:
        sink.description = body.description
    if body.filter is not None:
        sink.filter_config = body.filter.model_dump(exclude_none=True)
    if body.enabled is not None:
        sink.enabled = body.enabled
        # Operator-driven enable resets the circuit breaker.
        if body.enabled:
            sink.consecutive_failures = 0
            sink.circuit_opened_at = None

    new_secret = ""
    action = "sink_updated"
    if body.rotate_secret:
        new_secret = _generate_secret()
        sink.secret = new_secret
        action = "sink_secret_rotated"

    db.commit()
    db.refresh(sink)

    _audit_sink_lifecycle(db, user=user, sink=sink, action=action)

    return SinkCreatedResponse(
        id=sink.id,
        org_id=sink.org_id,
        name=sink.name,
        kind=sink.kind,
        url=sink.url,
        description=sink.description,
        enabled=sink.enabled,
        filter=sink.filter_config,
        consecutive_failures=sink.consecutive_failures,
        circuit_opened_at=sink.circuit_opened_at,
        created_at=sink.created_at,
        updated_at=sink.updated_at,
        created_by=sink.created_by,
        secret=new_secret,
    )


@router.delete(
    "/{sink_id}",
    status_code=204,
    summary="Soft-delete a sink",
)
def delete_sink(
    sink_id: uuid.UUID,
    force: bool = Query(
        False,
        description=(
            "Required when the sink has pending outbox rows. Drops the pending "
            "rows instead of waiting for them to drain."
        ),
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    org_id = _require_org_admin(db, user)
    sink = _get_sink_scoped(db, sink_id, org_id)

    pending = (
        db.query(AuditLogOutbox)
        .filter(
            AuditLogOutbox.sink_id == sink.id,
            AuditLogOutbox.status.in_((OutboxStatus.pending.value, OutboxStatus.failed.value)),
        )
        .count()
    )
    if pending > 0 and not force:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Sink has {pending} pending outbox rows. Wait for them to "
                "drain, or re-issue the DELETE with ?force=true to drop them."
            ),
        )

    if pending > 0:
        # Force path: mark the rows dead_letter so the FK RESTRICT is still
        # respected (we keep them for audit but stop attempting delivery).
        db.query(AuditLogOutbox).filter(
            AuditLogOutbox.sink_id == sink.id,
            AuditLogOutbox.status.in_((OutboxStatus.pending.value, OutboxStatus.failed.value)),
        ).update(
            {
                AuditLogOutbox.status: OutboxStatus.dead_letter.value,
                AuditLogOutbox.last_error: "sink force-deleted by operator",
            },
            synchronize_session=False,
        )

    sink.deleted_at = datetime.now(UTC)
    sink.enabled = False
    db.commit()

    _audit_sink_lifecycle(db, user=user, sink=sink, action="sink_deleted")


@router.post(
    "/{sink_id}/test",
    response_model=SinkTestResponse,
    summary="Send a synthetic test event to the sink",
)
def test_sink(
    sink_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SinkTestResponse:
    """Deliver a single synthetic event to the sink — does NOT touch the outbox.

    Use this right after creating a sink to verify the endpoint is
    reachable, the signature header is validated, and the customer's
    receiver accepts the envelope.
    """
    org_id = _require_org_admin(db, user)
    sink = _get_sink_scoped(db, sink_id, org_id)

    transport = TRANSPORTS.get(sink.kind)
    if transport is None:
        raise HTTPException(status_code=500, detail=f"No transport for sink kind {sink.kind!r}")

    test_event = {
        "id": 0,
        "agent_id": None,
        "agent_name": None,
        "org_id": str(org_id),
        "user_id": str(user.id),
        "correlation_id": f"test-{uuid.uuid4()}",
        "endpoint": "__test__",
        "method": "POST",
        "decision": "test",
        "cost_estimate_usd": None,
        "latency_ms": None,
        "request_metadata": {
            "action_type": "sink_test",
            "note": "Synthetic event from /api/v1/audit/sinks/{id}/test",
        },
        "entry_hash": "test",
        "prev_hash": "test",
        "created_at": datetime.now(UTC).isoformat(),
    }

    start = time.perf_counter()
    result = transport.deliver(events=[test_event], url=sink.url, secret=sink.secret)
    # Fall back to the transport's own latency if it was populated; otherwise
    # compute here so we always return one.
    latency_ms = (
        result.latency_ms
        if result.latency_ms is not None
        else int((time.perf_counter() - start) * 1000)
    )

    _audit_sink_lifecycle(db, user=user, sink=sink, action="sink_tested")

    return SinkTestResponse(
        sink_id=sink.id,
        delivered=result.success,
        status_code=result.status_code,
        latency_ms=latency_ms,
        error=result.error,
    )
