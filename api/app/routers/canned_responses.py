"""Canned response endpoints — pre-written responses for common support questions."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import CannedResponse, User, get_db
from common.schemas.canned_response import (
    CannedResponseCreate,
    CannedResponseListResponse,
    CannedResponseResponse,
    CannedResponseUpdate,
)

logger = logging.getLogger("ai_identity.api.canned_responses")

router = APIRouter(prefix="/api/v1/support/canned-responses", tags=["support"])


def _build_response(response: CannedResponse, db: Session) -> CannedResponseResponse:
    """Build a canned response with creator email."""
    creator = db.query(User).filter(User.id == response.created_by_user_id).first()
    return CannedResponseResponse(
        id=response.id,
        org_id=response.org_id,
        title=response.title,
        body=response.body,
        category=response.category,
        created_by_user_id=response.created_by_user_id,
        created_by_email=creator.email if creator else None,
        created_at=response.created_at,
        updated_at=response.updated_at,
    )


# ── GET /api/v1/support/canned-responses ─────────────────────────────


@router.get(
    "",
    response_model=CannedResponseListResponse,
    summary="List canned responses",
)
async def list_canned_responses(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in title and body"),
    limit: int = Query(50, ge=1, le=100, description="Number of responses to return"),
    offset: int = Query(0, ge=0, description="Number of responses to skip"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CannedResponseListResponse:
    """List canned responses for the user's organization.

    Supports filtering by category and searching by keyword.
    """
    if not user.org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization to access canned responses"
        )

    query = db.query(CannedResponse).filter(CannedResponse.org_id == user.org_id)

    # Apply filters
    if category:
        query = query.filter(CannedResponse.category == category)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                CannedResponse.title.ilike(search_pattern),
                CannedResponse.body.ilike(search_pattern),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    responses = query.order_by(CannedResponse.title).limit(limit).offset(offset).all()

    # Build response objects
    items = [_build_response(resp, db) for resp in responses]

    return CannedResponseListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ── POST /api/v1/support/canned-responses ────────────────────────────


@router.post(
    "",
    response_model=CannedResponseResponse,
    summary="Create a canned response",
    status_code=201,
)
async def create_canned_response(
    data: CannedResponseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CannedResponseResponse:
    """Create a new canned response (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create canned responses")

    if not user.org_id:
        raise HTTPException(
            status_code=400, detail="User must belong to an organization to create canned responses"
        )

    response = CannedResponse(
        org_id=user.org_id,
        title=data.title,
        body=data.body,
        category=data.category,
        created_by_user_id=user.id,
    )

    db.add(response)
    db.commit()
    db.refresh(response)

    logger.info(
        "Created canned response '%s' for org %s by user %s",
        response.title,
        response.org_id,
        user.email,
    )

    return _build_response(response, db)


# ── GET /api/v1/support/canned-responses/{response_id} ───────────────


@router.get(
    "/{response_id}",
    response_model=CannedResponseResponse,
    summary="Get canned response details",
)
async def get_canned_response(
    response_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CannedResponseResponse:
    """Get details of a specific canned response."""
    response = db.query(CannedResponse).filter(CannedResponse.id == response_id).first()

    if not response:
        raise HTTPException(status_code=404, detail="Canned response not found")

    # Check org access
    if response.org_id != user.org_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return _build_response(response, db)


# ── PATCH /api/v1/support/canned-responses/{response_id} ─────────────


@router.patch(
    "/{response_id}",
    response_model=CannedResponseResponse,
    summary="Update a canned response",
)
async def update_canned_response(
    response_id: UUID,
    data: CannedResponseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CannedResponseResponse:
    """Update a canned response (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update canned responses")

    response = db.query(CannedResponse).filter(CannedResponse.id == response_id).first()

    if not response:
        raise HTTPException(status_code=404, detail="Canned response not found")

    # Check org access
    if response.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    if data.title is not None:
        response.title = data.title
    if data.body is not None:
        response.body = data.body
    if data.category is not None:
        response.category = data.category

    response.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(response)

    logger.info("Updated canned response %s by user %s", response.id, user.email)

    return _build_response(response, db)


# ── DELETE /api/v1/support/canned-responses/{response_id} ────────────


@router.delete(
    "/{response_id}",
    status_code=204,
    summary="Delete a canned response",
)
async def delete_canned_response(
    response_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a canned response (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete canned responses")

    response = db.query(CannedResponse).filter(CannedResponse.id == response_id).first()

    if not response:
        raise HTTPException(status_code=404, detail="Canned response not found")

    # Check org access
    if response.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(response)
    db.commit()

    logger.info("Deleted canned response %s by user %s", response_id, user.email)


# Made with Bob
