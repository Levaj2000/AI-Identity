"""QA Checklist endpoints — run, list, and sign off on E2E QA runs."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.qa_runner import run_qa_checks
from common.config.settings import settings
from common.models import QARun, User, get_db

logger = logging.getLogger("ai_identity.api.qa")

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


# ── Helpers ──────────────────────────────────────────────────────────────


def _generate_run_id(db: Session) -> str:
    """Generate a date-based QA run ID like QA-20260321-003."""
    today = datetime.now(UTC)
    date_str = today.strftime("%Y%m%d")
    prefix = f"QA-{date_str}-"

    # Count how many runs exist today
    count = db.query(sa_func.count(QARun.id)).filter(QARun.run_id.like(f"{prefix}%")).scalar()
    return f"{prefix}{(count + 1):03d}"


# ── Schemas ─────────────────────────────────────────────────────────────


class QARunResponse(BaseModel):
    id: int
    run_id: str
    status: str
    run_by: str
    environment: str
    duration_ms: int
    passed_count: int
    failed_count: int
    total_count: int
    results: dict
    mode: str | None = None
    customer_signoff_by: str | None = None
    customer_signoff_at: datetime | None = None
    customer_signoff_note: str | None = None
    staff_signoff_by: str | None = None
    staff_signoff_at: datetime | None = None
    staff_signoff_note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QARunListResponse(BaseModel):
    items: list[QARunResponse]
    total: int


class SignoffRequest(BaseModel):
    role: str = Field(..., pattern="^(customer|staff)$", description="Who is signing off")
    note: str | None = Field(None, description="Optional sign-off note")


# ── POST /api/v1/qa/run — trigger a new QA run ─────────────────────────


@router.post(
    "/run",
    response_model=QARunResponse,
    status_code=201,
    summary="Run QA checklist",
    response_description="The completed QA run with all check results",
)
async def trigger_qa_run(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the 15-step E2E QA checklist against production.

    Creates temporary test resources (agent, policy, keys) and cleans them up.
    Results are persisted for sign-off tracking.
    """
    api_url = settings.gateway_url.replace(":8002", ":8001")
    # In production, use the public URLs
    if settings.environment == "production":
        api_url = "https://api.ai-identity.co"
        gateway_url = "https://gateway.ai-identity.co"
    else:
        api_url = f"http://localhost:{settings.api_port}"
        gateway_url = settings.gateway_url

    result = await run_qa_checks(api_url, gateway_url, user.email)

    run_id = _generate_run_id(db)
    qa_run = QARun(
        run_id=run_id,
        status="passed" if result.all_passed else "failed",
        run_by=user.email,
        environment=settings.environment,
        duration_ms=result.duration_ms,
        passed_count=result.passed,
        failed_count=result.failed,
        total_count=result.total,
        results=result.to_dict(),
        mode="admin",
        user_id=user.id,
    )
    db.add(qa_run)
    db.commit()
    db.refresh(qa_run)

    logger.info(
        "QA run %s by %s: %d/%d passed (%s)",
        qa_run.run_id,
        user.email,
        result.passed,
        result.total,
        "PASS" if result.all_passed else "FAIL",
    )

    return qa_run


# ── POST /api/v1/qa/run/onboarding — simulate client onboarding ──────


@router.post(
    "/run/onboarding",
    response_model=QARunResponse,
    status_code=201,
    summary="Simulate client onboarding",
    response_description="QA run executed as a fresh test client",
)
async def trigger_onboarding_run(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Simulate a full client onboarding flow.

    Creates a temporary test user account, runs all 15 QA checks as
    that user (fresh account, zero agents, zero history), then cleans
    up the test account. This validates the exact experience a new
    design partner will have.
    """
    # Determine environment URLs
    if settings.environment == "production":
        api_url = "https://api.ai-identity.co"
        gateway_url = "https://gateway.ai-identity.co"
    else:
        api_url = f"http://localhost:{settings.api_port}"
        gateway_url = settings.gateway_url

    # Create a temporary test user
    test_email = f"qa-client-{uuid.uuid4().hex[:8]}@test.ai-identity.co"
    test_user = User(
        id=uuid.uuid4(),
        email=test_email,
        role="owner",
        tier="free",
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    logger.info("Onboarding QA: created test user %s", test_email)

    try:
        result = await run_qa_checks(api_url, gateway_url, test_email)
    finally:
        # Clean up test user and any agents/resources they created
        # (cascade delete handles agents, keys, policies, audit entries)
        db.delete(test_user)
        db.commit()
        logger.info("Onboarding QA: cleaned up test user %s", test_email)

    run_id = _generate_run_id(db)
    qa_run = QARun(
        run_id=run_id,
        status="passed" if result.all_passed else "failed",
        run_by=user.email,
        environment=settings.environment,
        duration_ms=result.duration_ms,
        passed_count=result.passed,
        failed_count=result.failed,
        total_count=result.total,
        results=result.to_dict(),
        mode="onboarding",
        user_id=user.id,
    )
    db.add(qa_run)
    db.commit()
    db.refresh(qa_run)

    logger.info(
        "Onboarding QA run %s by %s (as %s): %d/%d passed (%s)",
        qa_run.run_id,
        user.email,
        test_email,
        result.passed,
        result.total,
        "PASS" if result.all_passed else "FAIL",
    )

    return qa_run


# ── GET /api/v1/qa/runs — list QA runs ─────────────────────────────────


@router.get(
    "/runs",
    response_model=QARunListResponse,
    summary="List QA runs",
)
def list_qa_runs(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all QA runs, newest first. Non-admin users only see their own runs."""
    query = db.query(QARun)
    if user.role != "admin":
        query = query.filter(QARun.user_id == user.id)
    total = query.count()
    runs = query.order_by(QARun.created_at.desc()).offset(offset).limit(limit).all()
    return QARunListResponse(items=runs, total=total)


# ── GET /api/v1/qa/has-pending — check for un-validated runs ────────────


class QAHasPendingResponse(BaseModel):
    has_pending: bool


@router.get(
    "/has-pending",
    response_model=QAHasPendingResponse,
    summary="Check for pending QA runs",
)
def qa_has_pending(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return true if there are QA runs awaiting staff sign-off.

    Non-admin users always get has_pending=false — the indicator
    is only meaningful for staff who validate onboarding runs.
    """
    if user.role != "admin":
        return QAHasPendingResponse(has_pending=False)

    exists = (
        db.query(QARun.id)
        .filter(QARun.staff_signoff_by.is_(None), QARun.status == "passed")
        .limit(1)
        .first()
    )
    return QAHasPendingResponse(has_pending=exists is not None)


# ── GET /api/v1/qa/runs/{run_id} — get a single QA run ─────────────────


@router.get(
    "/runs/{run_id}",
    response_model=QARunResponse,
    summary="Get QA run details",
)
def get_qa_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single QA run with full check results."""
    query = db.query(QARun).filter(QARun.run_id == run_id)
    if user.role != "admin":
        query = query.filter(QARun.user_id == user.id)
    run = query.first()
    if not run:
        raise HTTPException(status_code=404, detail="QA run not found")
    return run


# ── POST /api/v1/qa/runs/{run_id}/signoff — sign off on a QA run ───────


@router.post(
    "/runs/{run_id}/signoff",
    response_model=QARunResponse,
    summary="Sign off on a QA run",
)
def signoff_qa_run(
    run_id: str,
    body: SignoffRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sign off on a QA run as either customer or staff.

    Both customer and staff sign-offs are required for full validation.
    """
    query = db.query(QARun).filter(QARun.run_id == run_id)
    if user.role != "admin":
        query = query.filter(QARun.user_id == user.id)
    run = query.first()
    if not run:
        raise HTTPException(status_code=404, detail="QA run not found")

    now = datetime.now(UTC)

    if body.role == "customer":
        run.customer_signoff_by = user.email
        run.customer_signoff_at = now
        run.customer_signoff_note = body.note
    elif body.role == "staff":
        run.staff_signoff_by = user.email
        run.staff_signoff_at = now
        run.staff_signoff_note = body.note

    db.commit()
    db.refresh(run)

    logger.info("QA run %s signed off by %s (%s)", run_id, user.email, body.role)

    return run
