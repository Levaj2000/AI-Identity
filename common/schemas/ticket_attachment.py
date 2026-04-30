"""Pydantic schemas for ticket attachments."""

import datetime
import uuid

from pydantic import BaseModel, Field


class AttachmentUploadResponse(BaseModel):
    """Response after successful attachment upload."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    filename: str
    size_bytes: int
    content_type: str
    created_at: datetime.datetime


class AttachmentResponse(BaseModel):
    """Full attachment metadata response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    ticket_id: uuid.UUID
    comment_id: uuid.UUID | None
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_by: str | None = Field(None, description="Email of uploader")
    created_at: datetime.datetime


class AttachmentDownloadResponse(BaseModel):
    """Response with signed URL for download."""

    download_url: str
    expires_at: datetime.datetime
    filename: str
    content_type: str


class AttachmentListResponse(BaseModel):
    """List of attachments with summary."""

    attachments: list[AttachmentResponse]
    total_size_bytes: int
    count: int


# Made with Bob
