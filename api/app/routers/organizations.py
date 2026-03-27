"""Organization CRUD — create, manage, invite members, and delete orgs."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.models import Agent, User, get_db
from common.models.org_membership import OrgMembership, OrgRole
from common.models.organization import Organization
from common.schemas.organization import (
    OrgCreate,
    OrgMemberInvite,
    OrgMemberResponse,
    OrgMemberUpdate,
    OrgResponse,
    OrgUpdate,
)

logger = logging.getLogger("ai_identity.api.organizations")

router = APIRouter(prefix="/api/v1/orgs", tags=["organizations"])


# ── Helpers ───────────────────────────────────────────────────────────


def _org_response(org: Organization, db: Session) -> OrgResponse:
    """Build an OrgResponse with member and agent counts."""
    member_count = db.query(OrgMembership).filter(OrgMembership.org_id == org.id).count()
    agent_count = db.query(Agent).filter(Agent.org_id == org.id).count()
    return OrgResponse(
        id=org.id,
        name=org.name,
        owner_id=org.owner_id,
        tier=org.tier,
        member_count=member_count,
        agent_count=agent_count,
        created_at=org.created_at,
    )


def _require_membership(db: Session, user: User, *allowed_roles: str) -> OrgMembership:
    """Return the user's OrgMembership, or raise 403."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="No organization membership")
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == user.org_id,
            OrgMembership.user_id == user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership")
    if allowed_roles and membership.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient organization role")
    return membership


# ── POST /api/v1/orgs ─────────────────────────────────────────────────


@router.post("", response_model=OrgResponse, status_code=201, summary="Create organization")
def create_org(
    body: OrgCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new organization. The creator becomes the owner."""
    if user.org_id:
        raise HTTPException(status_code=400, detail="Already a member of an organization")

    org = Organization(
        id=uuid.uuid4(),
        name=body.name,
        owner_id=user.id,
    )
    db.add(org)

    # Create owner membership
    membership = OrgMembership(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        role=OrgRole.owner.value,
    )
    db.add(membership)

    # Set user's org_id
    user.org_id = org.id

    db.commit()
    db.refresh(org)

    logger.info("Organization created: %s (%s) by user %s", org.name, org.id, user.id)
    return _org_response(org, db)


# ── GET /api/v1/orgs/me ──────────────────────────────────────────────


@router.get("/me", response_model=OrgResponse, summary="Get my organization")
def get_my_org(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's organization."""
    if not user.org_id:
        raise HTTPException(status_code=404, detail="Not a member of any organization")
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _org_response(org, db)


# ── PATCH /api/v1/orgs/me ────────────────────────────────────────────


@router.patch("/me", response_model=OrgResponse, summary="Update organization")
def update_my_org(
    body: OrgUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update organization name. Requires owner or admin role."""
    _require_membership(db, user, OrgRole.owner.value, OrgRole.admin.value)

    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.name = body.name
    db.commit()
    db.refresh(org)

    logger.info("Organization updated: %s (%s)", org.name, org.id)
    return _org_response(org, db)


# ── DELETE /api/v1/orgs/me ───────────────────────────────────────────


@router.delete("/me", status_code=200, summary="Delete organization")
def delete_my_org(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the organization. Requires owner role.

    Clears org_id from all members and agents.
    """
    _require_membership(db, user, OrgRole.owner.value)

    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_id = org.id

    # Clear org_id from all members
    db.query(User).filter(User.org_id == org_id).update(
        {"org_id": None}, synchronize_session="fetch"
    )

    # Set agents' org_id to None
    db.query(Agent).filter(Agent.org_id == org_id).update(
        {"org_id": None}, synchronize_session="fetch"
    )

    # Delete the org (cascades to memberships)
    db.delete(org)
    db.commit()

    logger.info("Organization deleted: %s", org_id)
    return {"detail": "Organization deleted"}


# ── POST /api/v1/orgs/me/members ─────────────────────────────────────


@router.post(
    "/me/members", response_model=OrgMemberResponse, status_code=201, summary="Invite member"
)
def invite_member(
    body: OrgMemberInvite,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a user to the organization by email.

    If the user doesn't exist, they are auto-provisioned.
    Requires owner or admin role.
    """
    _require_membership(db, user, OrgRole.owner.value, OrgRole.admin.value)

    org_id = user.org_id

    # Find or create the target user
    target = db.query(User).filter(User.email == body.email).first()
    if not target:
        target = User(
            id=uuid.uuid4(),
            email=body.email,
            role="owner",
            tier="free",
        )
        db.add(target)
        db.flush()

    # Check if already a member
    existing = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == target.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this organization")

    # Check if user is in a different org
    if target.org_id and target.org_id != org_id:
        raise HTTPException(
            status_code=400, detail="User is already a member of another organization"
        )

    membership = OrgMembership(
        id=uuid.uuid4(),
        org_id=org_id,
        user_id=target.id,
        role=body.role,
    )
    db.add(membership)

    # Set their org_id
    target.org_id = org_id

    db.commit()
    db.refresh(membership)

    logger.info("Member invited: %s to org %s with role %s", body.email, org_id, body.role)
    return OrgMemberResponse(
        user_id=target.id,
        email=target.email,
        role=membership.role,
        joined_at=membership.created_at,
    )


# ── GET /api/v1/orgs/me/members ──────────────────────────────────────


@router.get("/me/members", response_model=list[OrgMemberResponse], summary="List members")
def list_members(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all members of the current organization."""
    if not user.org_id:
        raise HTTPException(status_code=404, detail="Not a member of any organization")

    memberships = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == user.org_id)
        .order_by(OrgMembership.created_at)
        .all()
    )

    results = []
    for m in memberships:
        member_user = db.query(User).filter(User.id == m.user_id).first()
        if member_user:
            results.append(
                OrgMemberResponse(
                    user_id=m.user_id,
                    email=member_user.email,
                    role=m.role,
                    joined_at=m.created_at,
                )
            )

    return results


# ── PATCH /api/v1/orgs/me/members/{user_id} ──────────────────────────


@router.patch(
    "/me/members/{user_id}",
    response_model=OrgMemberResponse,
    summary="Change member role",
)
def update_member_role(
    user_id: uuid.UUID,
    body: OrgMemberUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change a member's role. Only the org owner can change roles."""
    _require_membership(db, user, OrgRole.owner.value)

    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == user.org_id,
            OrgMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    # If transferring ownership, update the org owner_id and demote current owner
    if body.role == OrgRole.owner.value and membership.role != OrgRole.owner.value:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org.owner_id = user_id
        # Demote current owner to admin
        current_owner_membership = (
            db.query(OrgMembership)
            .filter(
                OrgMembership.org_id == user.org_id,
                OrgMembership.user_id == user.id,
            )
            .first()
        )
        if current_owner_membership:
            current_owner_membership.role = OrgRole.admin.value

    membership.role = body.role
    db.commit()
    db.refresh(membership)

    member_user = db.query(User).filter(User.id == user_id).first()
    logger.info("Member role updated: %s in org %s to %s", user_id, user.org_id, body.role)
    return OrgMemberResponse(
        user_id=membership.user_id,
        email=member_user.email if member_user else "",
        role=membership.role,
        joined_at=membership.created_at,
    )


# ── DELETE /api/v1/orgs/me/members/{user_id} ─────────────────────────


@router.delete(
    "/me/members/{user_id}",
    status_code=200,
    summary="Remove member",
)
def remove_member(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a member from the organization.

    Requires owner or admin role. Owners cannot be removed (transfer ownership first).
    """
    _require_membership(db, user, OrgRole.owner.value, OrgRole.admin.value)

    if user_id == user.id:
        raise HTTPException(
            status_code=400, detail="Cannot remove yourself. Transfer ownership or delete the org."
        )

    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == user.org_id,
            OrgMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    if membership.role == OrgRole.owner.value:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")

    # Clear the user's org_id
    target = db.query(User).filter(User.id == user_id).first()
    if target:
        target.org_id = None

    db.delete(membership)
    db.commit()

    logger.info("Member removed: %s from org %s", user_id, user.org_id)
    return {"detail": "Member removed"}
