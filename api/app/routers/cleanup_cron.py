"""Cleanup cron — internal endpoint for automated inactive user removal.

Called weekly by Render Cron Job. Not exposed in public API docs.
Secured by internal service key.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from common.config.settings import settings
from common.models import User, get_db
from common.queries.user_cleanup import PROTECTED_EMAILS, delete_users_with_cascade

logger = logging.getLogger("ai_identity.api.cleanup_cron")

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/cleanup/inactive-users", include_in_schema=False)
def cleanup_inactive_users(
    db: Session = Depends(get_db),
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
    inactivity_days: int = Query(90, ge=30, le=365, description="Days of inactivity threshold"),
    dry_run: bool = Query(True, description="Preview without deleting"),
):
    """Delete free-tier users inactive for N days.

    Protection criteria — users are NEVER eligible if:
    - tier is not "free"
    - role is "admin"
    - has a stripe_customer_id or stripe_subscription_id
    - email is in the protected allowlist
    """
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cutoff = datetime.now(UTC) - timedelta(days=inactivity_days)

    # Find inactive free-tier users
    eligible = (
        db.query(User)
        .filter(
            User.tier == "free",
            User.role != "admin",
            User.updated_at <= cutoff,
            User.stripe_customer_id.is_(None),
            User.stripe_subscription_id.is_(None),
            User.email.notin_(PROTECTED_EMAILS),
        )
        .all()
    )

    if dry_run:
        return {
            "status": "dry_run",
            "eligible": len(eligible),
            "deleted": 0,
            "dry_run": True,
            "eligible_emails": [u.email for u in eligible],
            "inactivity_days": inactivity_days,
        }

    result = delete_users_with_cascade(db, eligible)

    logger.info(
        "Inactive user cleanup: deleted %d users (inactivity_days=%d)",
        result["deleted_count"],
        inactivity_days,
    )

    return {
        "status": "ok",
        "eligible": len(eligible),
        "deleted": result["deleted_count"],
        "dry_run": False,
        "deleted_emails": result["emails"],
        "agents_removed": result["agents_removed"],
        "inactivity_days": inactivity_days,
    }
