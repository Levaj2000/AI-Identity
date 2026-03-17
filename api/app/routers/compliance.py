"""Compliance endpoints — frameworks, assessments, reports, and status."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.compliance_engine import run_assessment
from common.models import (
    ComplianceCheck,
    ComplianceFramework,
    ComplianceReport,
    User,
    get_db,
)
from common.schemas.compliance import (
    ComplianceFrameworkListResponse,
    ComplianceFrameworkResponse,
    ComplianceReportCreate,
    ComplianceReportListResponse,
    ComplianceReportResponse,
    ComplianceResultResponse,
    ComplianceStatusResponse,
)

logger = logging.getLogger("ai_identity.api.compliance")

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


# ── GET /api/v1/compliance/frameworks ────────────────────────────────


@router.get(
    "/frameworks",
    response_model=ComplianceFrameworkListResponse,
    summary="List compliance frameworks",
)
def list_frameworks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all available compliance frameworks with their checks."""
    frameworks = db.query(ComplianceFramework).order_by(ComplianceFramework.name).all()
    return ComplianceFrameworkListResponse(
        items=[ComplianceFrameworkResponse.model_validate(f) for f in frameworks],
        total=len(frameworks),
    )


# ── GET /api/v1/compliance/frameworks/{id} ───────────────────────────


@router.get(
    "/frameworks/{framework_id}",
    response_model=ComplianceFrameworkResponse,
    summary="Get framework details",
)
def get_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific compliance framework with all its checks."""
    framework = db.query(ComplianceFramework).filter(ComplianceFramework.id == framework_id).first()
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")
    return ComplianceFrameworkResponse.model_validate(framework)


# ── POST /api/v1/compliance/reports ──────────────────────────────────


@router.post(
    "/reports",
    response_model=ComplianceReportResponse,
    status_code=201,
    summary="Run compliance assessment",
)
def create_report(
    body: ComplianceReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run a compliance assessment against a framework.

    Creates a report, evaluates all automated checks, and returns
    the results with a compliance score. If `agent_id` is provided,
    the assessment is scoped to that specific agent; otherwise it
    runs across all agents owned by the user.
    """
    # Validate framework exists
    framework = (
        db.query(ComplianceFramework).filter(ComplianceFramework.id == body.framework_id).first()
    )
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")

    # Get checks for this framework
    checks = db.query(ComplianceCheck).filter(ComplianceCheck.framework_id == framework.id).all()

    # Create report
    report = ComplianceReport(
        user_id=user.id,
        framework_id=framework.id,
        agent_id=body.agent_id,
        status="running",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Run automated evaluation
    run_assessment(db, report, checks, user.id, body.agent_id)
    db.refresh(report)

    # Build response
    return _build_report_response(report, framework)


# ── GET /api/v1/compliance/reports ───────────────────────────────────


@router.get(
    "/reports",
    response_model=ComplianceReportListResponse,
    summary="List compliance reports",
)
def list_reports(
    framework_id: int | None = Query(None, description="Filter by framework"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List past compliance assessment reports."""
    query = db.query(ComplianceReport).filter(ComplianceReport.user_id == user.id)
    if framework_id:
        query = query.filter(ComplianceReport.framework_id == framework_id)

    total = query.count()
    reports = query.order_by(ComplianceReport.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for report in reports:
        framework = (
            db.query(ComplianceFramework)
            .filter(ComplianceFramework.id == report.framework_id)
            .first()
        )
        items.append(_build_report_response(report, framework, include_results=False))

    return ComplianceReportListResponse(items=items, total=total)


# ── GET /api/v1/compliance/reports/{id} ──────────────────────────────


@router.get(
    "/reports/{report_id}",
    response_model=ComplianceReportResponse,
    summary="Get report details",
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a compliance report with full results."""
    report = (
        db.query(ComplianceReport)
        .filter(
            ComplianceReport.id == report_id,
            ComplianceReport.user_id == user.id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    framework = (
        db.query(ComplianceFramework).filter(ComplianceFramework.id == report.framework_id).first()
    )

    return _build_report_response(report, framework)


# ── GET /api/v1/compliance/status ────────────────────────────────────


@router.get(
    "/status",
    response_model=ComplianceStatusResponse,
    summary="Overall compliance posture",
)
def compliance_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get an overall compliance posture summary across all frameworks.

    Returns the latest report per framework, aggregate scores, and
    critical failures needing attention.
    """
    # Get all frameworks
    frameworks = db.query(ComplianceFramework).all()

    latest_reports = []
    all_scores = []
    total_checks = 0
    checks_passed = 0
    checks_failed = 0
    checks_warning = 0
    critical_failures = []

    for framework in frameworks:
        # Get latest completed report for this framework
        latest = (
            db.query(ComplianceReport)
            .filter(
                ComplianceReport.user_id == user.id,
                ComplianceReport.framework_id == framework.id,
                ComplianceReport.status == "completed",
            )
            .order_by(ComplianceReport.created_at.desc())
            .first()
        )

        if latest:
            report_resp = _build_report_response(latest, framework)
            latest_reports.append(report_resp)

            if latest.score is not None:
                all_scores.append(float(latest.score))

            # Count results
            for result in latest.results:
                total_checks += 1
                if result.status == "pass":
                    checks_passed += 1
                elif result.status == "fail":
                    checks_failed += 1
                    # Track critical/high failures
                    check = (
                        db.query(ComplianceCheck)
                        .filter(ComplianceCheck.id == result.check_id)
                        .first()
                    )
                    if check and check.severity in ("critical", "high"):
                        critical_failures.append(
                            {
                                "check_code": check.code,
                                "check_name": check.name,
                                "severity": check.severity,
                                "framework": framework.name,
                                "remediation": result.remediation,
                            }
                        )
                elif result.status == "warning":
                    checks_warning += 1

    overall_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

    return ComplianceStatusResponse(
        overall_score=overall_score,
        frameworks_assessed=len(latest_reports),
        total_checks=total_checks,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        checks_warning=checks_warning,
        critical_failures=critical_failures,
        latest_reports=latest_reports,
    )


# ── Helpers ──────────────────────────────────────────────────────────


def _build_report_response(
    report: ComplianceReport,
    framework: ComplianceFramework | None,
    include_results: bool = True,
) -> ComplianceReportResponse:
    """Build a report response with optional results."""
    results = []
    if include_results:
        for result in report.results:
            results.append(
                ComplianceResultResponse(
                    id=result.id,
                    check_id=result.check_id,
                    check=result.check,
                    status=result.status,
                    evidence=result.evidence,
                    remediation=result.remediation,
                )
            )

    return ComplianceReportResponse(
        id=report.id,
        user_id=report.user_id,
        framework_id=report.framework_id,
        framework_name=framework.name if framework else None,
        agent_id=report.agent_id,
        status=report.status,
        score=float(report.score) if report.score else None,
        summary=report.summary,
        results=results,
        created_at=report.created_at,
    )
