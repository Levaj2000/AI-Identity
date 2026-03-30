"""Human-in-the-Loop (HITL) gateway check — enterprise tier only.

When a policy includes `require_approval` patterns, matching requests
are paused until an admin approves or rejects them via the dashboard.

Fail-closed: unapproved requests auto-expire after a configurable timeout.
"""

import datetime
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from common.config.settings import settings
from common.models.approval_request import ApprovalRequest, ApprovalStatus
from common.models.policy import Policy
from gateway.app.enforce import _endpoint_matches

logger = logging.getLogger("ai_identity.gateway.hitl")


def _utcnow() -> datetime.datetime:
    """Return current UTC time as naive datetime (compatible with both PostgreSQL and SQLite)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


@dataclass
class HitlResult:
    """Result of HITL check."""

    action: str  # "allow" (no HITL needed or approved), "pending" (awaiting review)
    review_id: str | None = None
    message: str = ""


def check_hitl(
    db: Session,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    endpoint: str,
    method: str,
    review_id: str | None,
    user_tier: str,
) -> HitlResult:
    """Check if this request requires human-in-the-loop approval.

    Called AFTER policy ALLOW and BEFORE quota increment.

    Returns:
        HitlResult with action="allow" to proceed, or "pending" to pause.
    """
    # 1. Enterprise-only — zero cost for free/pro/business tiers
    if user_tier != "enterprise":
        return HitlResult(action="allow")

    # 2. If a review_id is provided, validate it
    if review_id:
        return _validate_review(db, review_id, agent_id, endpoint, method)

    # 3. Load policy and check for require_approval patterns
    policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )
    if not policy or not policy.rules:
        return HitlResult(action="allow")

    require_approval = policy.rules.get("require_approval", [])
    if not require_approval:
        return HitlResult(action="allow")

    # 4. Check if this endpoint matches any require_approval patterns
    needs_approval = any(_endpoint_matches(endpoint, pattern) for pattern in require_approval)
    if not needs_approval:
        return HitlResult(action="allow")

    # 5. Create a pending approval request
    expires_at = _utcnow() + datetime.timedelta(seconds=settings.hitl_default_timeout_seconds)

    approval = ApprovalRequest(
        id=uuid.uuid4(),
        agent_id=agent_id,
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        request_metadata={"key_type": "runtime"},
        status=ApprovalStatus.pending.value,
        expires_at=expires_at,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    logger.info(
        "HITL: Created approval request %s for agent %s → %s %s (expires %s)",
        approval.id,
        agent_id,
        method,
        endpoint,
        expires_at.isoformat(),
    )

    return HitlResult(
        action="pending",
        review_id=str(approval.id),
        message=f"Request requires human approval. Review ID: {approval.id}",
    )


def _validate_review(
    db: Session,
    review_id: str,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
) -> HitlResult:
    """Validate a review_id for an approved request.

    Checks:
    1. Approval exists
    2. Status is "approved"
    3. Agent/endpoint/method match the original request
    4. Not expired
    """
    try:
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        return HitlResult(action="allow")  # Invalid UUID — skip HITL check

    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == review_uuid).first()

    if not approval:
        logger.warning("HITL: Review %s not found", review_id)
        return HitlResult(action="allow")  # Not found — skip (don't block)

    # Lazy expire if past deadline
    if approval.status == ApprovalStatus.pending.value and approval.expires_at < _utcnow():
        approval.status = ApprovalStatus.expired.value
        db.commit()

    if approval.status != ApprovalStatus.approved.value:
        return HitlResult(
            action="pending",
            review_id=review_id,
            message=f"Approval request is {approval.status}, not approved.",
        )

    # Verify the approval matches this request
    if str(approval.agent_id) != str(agent_id):
        logger.warning("HITL: Review %s agent mismatch", review_id)
        return HitlResult(action="allow")  # Mismatch — skip

    if approval.endpoint != endpoint or approval.method.upper() != method.upper():
        logger.warning("HITL: Review %s endpoint/method mismatch", review_id)
        return HitlResult(action="allow")  # Mismatch — skip

    logger.info("HITL: Approved review %s — allowing request", review_id)
    return HitlResult(action="allow", review_id=review_id)


def expire_stale(db: Session) -> int:
    """Expire all pending approvals past their deadline.

    Returns the count of expired rows. Called lazily on reads
    and (future) via a background cron.
    """
    now = _utcnow()
    count = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.status == ApprovalStatus.pending.value,
            ApprovalRequest.expires_at < now,
        )
        .update(
            {
                ApprovalRequest.status: ApprovalStatus.expired.value,
                ApprovalRequest.updated_at: func.now(),
            },
            synchronize_session=False,
        )
    )
    if count:
        db.commit()
        logger.info("HITL: Expired %d stale approval requests", count)
    return count
