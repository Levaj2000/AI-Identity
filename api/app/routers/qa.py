"""QA Checklist endpoints — run, list, and sign off on E2E QA runs."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.qa_runner import run_qa_checks
from common.config.settings import settings
from common.models import QARun, User, get_db

logger = logging.getLogger("ai_identity.api.qa")

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


# ── Schemas ─────────────────────────────────────────────────────────────


class QARunResponse(BaseModel):
    id: int
    status: str
    run_by: str
    environment: str
    duration_ms: int
    passed_count: int
    failed_count: int
    total_count: int
    results: dict
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
    # In production, use the Render URLs
    if settings.environment == "production":
        api_url = "https://ai-identity-api.onrender.com"
        gateway_url = "https://ai-identity-gateway.onrender.com"
    else:
        api_url = f"http://localhost:{settings.api_port}"
        gateway_url = settings.gateway_url

    result = await run_qa_checks(api_url, gateway_url, user.email)

    qa_run = QARun(
        status="passed" if result.all_passed else "failed",
        run_by=user.email,
        environment=settings.environment,
        duration_ms=result.duration_ms,
        passed_count=result.passed,
        failed_count=result.failed,
        total_count=result.total,
        results=result.to_dict(),
    )
    db.add(qa_run)
    db.commit()
    db.refresh(qa_run)

    logger.info(
        "QA run #%d by %s: %d/%d passed (%s)",
        qa_run.id,
        user.email,
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
    """List all QA runs, newest first."""
    total = db.query(QARun).count()
    runs = db.query(QARun).order_by(QARun.created_at.desc()).offset(offset).limit(limit).all()
    return QARunListResponse(items=runs, total=total)


# ── GET /api/v1/qa/runs/{run_id} — get a single QA run ─────────────────


@router.get(
    "/runs/{run_id}",
    response_model=QARunResponse,
    summary="Get QA run details",
)
def get_qa_run(
    run_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single QA run with full check results."""
    run = db.query(QARun).filter(QARun.id == run_id).first()
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
    run_id: int,
    body: SignoffRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sign off on a QA run as either customer or staff.

    Both customer and staff sign-offs are required for full validation.
    """
    run = db.query(QARun).filter(QARun.id == run_id).first()
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

    logger.info("QA run #%d signed off by %s (%s)", run_id, user.email, body.role)

    return run
