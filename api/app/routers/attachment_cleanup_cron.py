"""Background job to clean up deleted attachments."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from common.config.settings import settings
from common.models import SupportTicket, get_db
from common.models.support_ticket import TicketStatus
from common.models.ticket_attachment import TicketAttachment
from common.storage import get_storage_backend

logger = logging.getLogger("ai_identity.api.attachment_cleanup")

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])


def get_storage():
    """Dependency to get storage backend."""
    return get_storage_backend(settings)


@router.post("/attachment-cleanup")
async def cleanup_attachments(
    x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None,
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
):
    """Hard-delete attachments that meet deletion criteria.

    Two deletion cases:
    1. Soft-deleted attachments older than 30 days
    2. Attachments from tickets closed for 90+ days

    This endpoint requires internal service authentication via X-Internal-Key header.
    It's designed to be called by a Kubernetes CronJob.

    Returns:
        Dict with deletion statistics and any errors encountered

    Raises:
        401: Missing or invalid internal service key
    """
    # Verify internal service key
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    now = datetime.now(UTC)
    soft_delete_cutoff = now - timedelta(days=30)
    closed_ticket_cutoff = now - timedelta(days=90)

    deleted_count = 0
    errors = []

    # Case 1: Soft-deleted attachments older than 30 days
    logger.info("Starting cleanup of soft-deleted attachments older than 30 days")

    soft_deleted_attachments = (
        db.query(TicketAttachment)
        .filter(TicketAttachment.deleted_at < soft_delete_cutoff)
        .yield_per(1000)
    )

    for attachment in soft_deleted_attachments:
        try:
            # Delete from storage
            await storage.delete(attachment.storage_path)

            # Delete from database
            db.delete(attachment)
            db.commit()

            deleted_count += 1

            logger.info(
                "Hard-deleted soft-deleted attachment %s (ticket %s, deleted %s)",
                attachment.id,
                attachment.ticket_id,
                attachment.deleted_at,
            )

        except FileNotFoundError:
            # File already gone from storage - just delete DB record
            logger.warning(
                "Storage file not found for attachment %s, deleting DB record only",
                attachment.id,
            )
            try:
                db.delete(attachment)
                db.commit()
                deleted_count += 1
            except Exception as e:
                db.rollback()
                error_msg = f"Failed to delete DB record for attachment {attachment.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        except Exception as e:
            db.rollback()
            error_msg = f"Failed to delete attachment {attachment.id}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Case 2: Attachments from closed tickets past retention period (90 days)
    logger.info("Starting cleanup of attachments from closed tickets older than 90 days")

    closed_ticket_attachments = (
        db.query(TicketAttachment)
        .join(SupportTicket, TicketAttachment.ticket_id == SupportTicket.id)
        .filter(
            TicketAttachment.deleted_at.is_(None),  # Not already soft-deleted
            SupportTicket.status == TicketStatus.CLOSED,
            SupportTicket.closed_at < closed_ticket_cutoff,
        )
        .yield_per(1000)
    )

    for attachment in closed_ticket_attachments:
        try:
            # Delete from storage
            await storage.delete(attachment.storage_path)

            # Delete from database
            db.delete(attachment)
            db.commit()

            deleted_count += 1

            logger.info(
                "Hard-deleted attachment %s from closed ticket %s",
                attachment.id,
                attachment.ticket_id,
            )

        except FileNotFoundError:
            # File already gone from storage - just delete DB record
            logger.warning(
                "Storage file not found for attachment %s, deleting DB record only",
                attachment.id,
            )
            try:
                db.delete(attachment)
                db.commit()
                deleted_count += 1
            except Exception as e:
                db.rollback()
                error_msg = f"Failed to delete DB record for attachment {attachment.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        except Exception as e:
            db.rollback()
            error_msg = f"Failed to delete attachment {attachment.id}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    logger.info(
        "Attachment cleanup complete: deleted %d attachments, %d errors",
        deleted_count,
        len(errors),
    )

    return {
        "deleted": deleted_count,
        "errors": errors,
        "timestamp": now.isoformat(),
    }


# Made with Bob
