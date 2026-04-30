"""Attachment endpoints for support tickets."""

import contextlib
import hashlib
import logging
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.routers.support_tickets import _can_access_ticket
from common.config.settings import Settings
from common.models import SupportTicket, TicketComment, User, get_db
from common.models.ticket_attachment import TicketAttachment
from common.schemas.ticket_attachment import (
    AttachmentDownloadResponse,
    AttachmentListResponse,
    AttachmentResponse,
    AttachmentUploadResponse,
)
from common.security.exif_strip import strip_exif
from common.security.filename import generate_storage_path, sanitize_filename
from common.security.virus_scan import scan_file
from common.storage import get_storage_backend
from common.validation.file_upload import (
    MAX_ATTACHMENTS_PER_COMMENT,
    MAX_ATTACHMENTS_PER_TICKET,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_SIZE_PER_TICKET,
    is_image,
    validate_file_upload,
)

logger = logging.getLogger("ai_identity.api.attachments")

router = APIRouter(prefix="/api/v1/support/attachments", tags=["attachments"])

# Dependency to get settings
settings = Settings()


def get_storage():
    """Dependency to get storage backend."""
    return get_storage_backend(settings)


@router.post(
    "/upload",
    response_model=AttachmentUploadResponse,
    summary="Upload attachment to ticket or comment",
    status_code=201,
)
async def upload_attachment(
    file: UploadFile = File(...),
    ticket_id: uuid.UUID = Form(...),
    comment_id: uuid.UUID | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
):
    """Upload file attachment to a support ticket or comment.

    Security validations:
    - File size limit (10 MB per file)
    - Total size limit per ticket (100 MB)
    - Attachment count limits (20 per ticket, 10 per comment)
    - Magic byte content type validation
    - Virus scanning (ClamAV)
    - EXIF stripping for images
    - Filename sanitization

    Args:
        file: File to upload
        ticket_id: Parent ticket ID
        comment_id: Optional comment ID (if attaching to comment)
        user: Current authenticated user
        db: Database session
        storage: Storage backend

    Returns:
        Attachment metadata

    Raises:
        403: User doesn't have access to ticket
        404: Ticket or comment not found
        413: File too large or quota exceeded
        415: Invalid file type or virus detected
        422: Validation error
    """
    # Get and validate ticket
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check access using canonical function
    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Validate comment if provided
    if comment_id:
        comment = (
            db.query(TicketComment)
            .filter(
                TicketComment.id == comment_id,
                TicketComment.ticket_id == ticket_id,
            )
            .first()
        )

        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

    # Check attachment count limits
    ticket_attachment_count = (
        db.query(func.count(TicketAttachment.id))
        .filter(
            TicketAttachment.ticket_id == ticket_id,
            TicketAttachment.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    if ticket_attachment_count >= MAX_ATTACHMENTS_PER_TICKET:
        raise HTTPException(
            status_code=413,
            detail=f"Maximum {MAX_ATTACHMENTS_PER_TICKET} attachments per ticket",
        )

    if comment_id:
        comment_attachment_count = (
            db.query(func.count(TicketAttachment.id))
            .filter(
                TicketAttachment.comment_id == comment_id,
                TicketAttachment.deleted_at.is_(None),
            )
            .scalar()
            or 0
        )

        if comment_attachment_count >= MAX_ATTACHMENTS_PER_COMMENT:
            raise HTTPException(
                status_code=413,
                detail=f"Maximum {MAX_ATTACHMENTS_PER_COMMENT} attachments per comment",
            )

    # Check total size limit
    total_size = (
        db.query(func.sum(TicketAttachment.size_bytes))
        .filter(
            TicketAttachment.ticket_id == ticket_id,
            TicketAttachment.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    if total_size >= MAX_TOTAL_SIZE_PER_TICKET:
        raise HTTPException(
            status_code=413,
            detail=f"Maximum {MAX_TOTAL_SIZE_PER_TICKET} bytes per ticket",
        )

    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        tmp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)

    try:
        # Validate file size
        file_size = tmp_path.stat().st_size

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes (max {MAX_FILE_SIZE_BYTES})",
            )

        if total_size + file_size > MAX_TOTAL_SIZE_PER_TICKET:
            raise HTTPException(
                status_code=413,
                detail=f"Would exceed ticket size limit of {MAX_TOTAL_SIZE_PER_TICKET} bytes",
            )

        # Validate content type using magic bytes
        content_type, error = await validate_file_upload(
            tmp_path,
            claimed_content_type=file.content_type,
            max_size_bytes=MAX_FILE_SIZE_BYTES,
        )

        if error:
            raise HTTPException(status_code=415, detail=error)

        # Strip EXIF metadata from images
        if is_image(content_type):
            try:
                await strip_exif(tmp_path)
            except Exception as e:
                logger.error("Failed to strip EXIF from %s: %s", file.filename, str(e))
                raise HTTPException(status_code=422, detail="Failed to process image") from e

        # Scan for viruses
        is_clean, threat = await scan_file(tmp_path)

        if not is_clean:
            logger.warning("Virus detected in upload from user %s: %s", user.id, threat)
            raise HTTPException(
                status_code=415,
                detail=f"File rejected by virus scanner: {threat}",
            )

        # Compute SHA-256 hash
        sha256_hash = hashlib.sha256()
        with open(tmp_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        sha256 = sha256_hash.hexdigest()

        # Generate attachment ID and storage path
        attachment_id = uuid.uuid4()
        sanitized_filename = sanitize_filename(file.filename)

        parent_type = "comment" if comment_id else "ticket"
        parent_id = str(comment_id) if comment_id else str(ticket_id)

        storage_path = generate_storage_path(
            org_id=str(ticket.org_id),
            attachment_id=str(attachment_id),
            original_filename=file.filename,
            parent_type=parent_type,
            parent_id=parent_id,
        )

        # Upload to storage backend
        try:
            await storage.upload(tmp_path, storage_path, content_type)
        except Exception as e:
            logger.error("Failed to upload to storage: %s", str(e))
            raise HTTPException(status_code=500, detail="Failed to upload file") from e

        # Create database record
        attachment = TicketAttachment(
            id=attachment_id,
            ticket_id=ticket_id,
            comment_id=comment_id,
            user_id=user.id,
            org_id=ticket.org_id,
            filename=sanitized_filename,
            original_filename=file.filename,
            content_type=content_type,
            size_bytes=file_size,
            sha256=sha256,
            storage_path=storage_path,
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        logger.info(
            "Uploaded attachment %s to ticket %s (user %s, size %d bytes)",
            attachment.id,
            ticket_id,
            user.id,
            file_size,
        )

        return AttachmentUploadResponse(
            id=attachment.id,
            filename=attachment.original_filename,
            size_bytes=attachment.size_bytes,
            content_type=attachment.content_type,
            created_at=attachment.created_at,
        )

    finally:
        # Clean up temporary file
        with contextlib.suppress(Exception):
            tmp_path.unlink()


@router.get(
    "/{attachment_id}/download",
    response_model=AttachmentDownloadResponse,
    summary="Get signed URL for attachment download",
)
async def download_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
):
    """Generate signed URL for downloading attachment.

    Returns a time-limited URL (1 hour expiration) that allows direct download
    from the storage backend without further authentication.

    Args:
        attachment_id: Attachment ID
        user: Current authenticated user
        db: Database session
        storage: Storage backend

    Returns:
        Signed URL and metadata

    Raises:
        404: Attachment not found or user doesn't have access
    """
    # Get attachment
    attachment = (
        db.query(TicketAttachment)
        .filter(
            TicketAttachment.id == attachment_id,
            TicketAttachment.deleted_at.is_(None),
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Get parent ticket
    ticket = db.query(SupportTicket).filter(SupportTicket.id == attachment.ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Parent ticket not found")

    # Check access using canonical function
    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Generate signed URL
    try:
        signed_url, expires_at = await storage.generate_signed_url(
            attachment.storage_path,
            expiration=timedelta(hours=1),
        )
    except FileNotFoundError as fnf:
        logger.error(
            "Storage file not found for attachment %s: %s",
            attachment.id,
            attachment.storage_path,
        )
        raise HTTPException(status_code=404, detail="Attachment file not found in storage") from fnf
    except Exception as e:
        logger.error("Failed to generate signed URL: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to generate download URL") from e

    logger.info(
        "Generated download URL for attachment %s (user %s)",
        attachment.id,
        user.id,
    )

    return AttachmentDownloadResponse(
        download_url=signed_url,
        expires_at=expires_at,
        filename=attachment.original_filename,
        content_type=attachment.content_type,
    )


@router.get(
    "/ticket/{ticket_id}",
    response_model=AttachmentListResponse,
    summary="List attachments for a ticket",
)
async def list_ticket_attachments(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all attachments for a ticket.

    Args:
        ticket_id: Ticket ID
        user: Current authenticated user
        db: Database session

    Returns:
        List of attachments with summary

    Raises:
        404: Ticket not found or user doesn't have access
    """
    # Get and validate ticket
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check access
    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get attachments
    attachments = (
        db.query(TicketAttachment, User.email)
        .outerjoin(User, TicketAttachment.user_id == User.id)
        .filter(
            TicketAttachment.ticket_id == ticket_id,
            TicketAttachment.deleted_at.is_(None),
        )
        .order_by(TicketAttachment.created_at.desc())
        .all()
    )

    # Build response
    attachment_responses = []
    total_size = 0

    for attachment, uploader_email in attachments:
        attachment_responses.append(
            AttachmentResponse(
                id=attachment.id,
                ticket_id=attachment.ticket_id,
                comment_id=attachment.comment_id,
                filename=attachment.filename,
                original_filename=attachment.original_filename,
                content_type=attachment.content_type,
                size_bytes=attachment.size_bytes,
                sha256=attachment.sha256,
                uploaded_by=uploader_email,
                created_at=attachment.created_at,
            )
        )
        total_size += attachment.size_bytes

    return AttachmentListResponse(
        attachments=attachment_responses,
        total_size_bytes=total_size,
        count=len(attachment_responses),
    )


@router.delete(
    "/{attachment_id}",
    status_code=204,
    summary="Delete attachment (soft delete)",
)
async def delete_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete an attachment.

    Only the uploader or an admin can delete an attachment.
    The file is marked as deleted but not immediately removed from storage.
    A background job will hard-delete it after 30 days.

    Args:
        attachment_id: Attachment ID
        user: Current authenticated user
        db: Database session

    Raises:
        403: User doesn't have permission to delete
        404: Attachment not found
    """
    # Get attachment
    attachment = (
        db.query(TicketAttachment)
        .filter(
            TicketAttachment.id == attachment_id,
            TicketAttachment.deleted_at.is_(None),
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Get parent ticket
    ticket = db.query(SupportTicket).filter(SupportTicket.id == attachment.ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Parent ticket not found")

    # Check access - must be uploader or admin
    if not _can_access_ticket(user, ticket):
        raise HTTPException(status_code=404, detail="Attachment not found")

    if user.role != "admin" and attachment.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the uploader or an admin can delete this attachment",
        )

    # Soft delete
    attachment.deleted_at = datetime.now(UTC)
    db.commit()

    logger.info(
        "Soft-deleted attachment %s (user %s)",
        attachment.id,
        user.id,
    )

    return None


# Made with Bob
