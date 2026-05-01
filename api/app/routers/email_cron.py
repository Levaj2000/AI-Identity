"""Email cron — internal endpoint for scheduled email sends.

Called daily by the ``daily-email-followups`` K8s CronJob
(see ``k8s/cronjob-email.yaml``). Not exposed in public API docs.
Secured by internal service key.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.app.email import send_followup_email
from common.config.settings import settings
from common.models import User, get_db

logger = logging.getLogger("ai_identity.api.email_cron")

router = APIRouter(prefix="/api/internal", tags=["internal"])


@router.post("/email/send-followups", include_in_schema=False)
def send_followup_emails(
    db: Session = Depends(get_db),
    x_internal_key: str | None = Header(None, alias="x-internal-key"),
):
    """Find users eligible for 5-day follow-up and send emails.

    Criteria: welcome email sent 5+ days ago, no follow-up sent yet.
    """
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cutoff = datetime.now(UTC) - timedelta(days=5)
    eligible_users = (
        db.query(User)
        .filter(
            User.welcome_email_sent_at.isnot(None),
            User.welcome_email_sent_at <= cutoff,
            User.followup_email_sent_at.is_(None),
        )
        .all()
    )

    sent_count = 0
    for user in eligible_users:
        result = send_followup_email(user.email)
        if result:
            user.followup_email_sent_at = datetime.now(UTC)
            sent_count += 1

    db.commit()
    logger.info("Follow-up cron: eligible=%d, sent=%d", len(eligible_users), sent_count)
    return {"status": "ok", "eligible": len(eligible_users), "sent": sent_count}
