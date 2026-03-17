"""Pydantic schemas for Compliance endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Framework Schemas ────────────────────────────────────────────────


class ComplianceCheckResponse(BaseModel):
    """A single compliance check within a framework."""

    id: int
    code: str = Field(description="Check code, e.g., NIST-GOV-01")
    name: str
    description: str | None = None
    severity: str = Field(description="critical, high, medium, low")
    category: str = Field(description="governance, security, transparency, accountability")
    check_type: str = Field(description="automated, manual, hybrid")

    model_config = {"from_attributes": True}


class ComplianceFrameworkResponse(BaseModel):
    """A compliance framework with its checks."""

    id: int
    name: str
    version: str
    description: str | None = None
    category: str = Field(description="regulatory, industry, internal")
    checks: list[ComplianceCheckResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceFrameworkListResponse(BaseModel):
    """List of available compliance frameworks."""

    items: list[ComplianceFrameworkResponse]
    total: int


# ── Report Schemas ───────────────────────────────────────────────────


class ComplianceReportCreate(BaseModel):
    """Request body for running a compliance assessment."""

    framework_id: int = Field(description="ID of the framework to assess against")
    agent_id: uuid.UUID | None = Field(
        None,
        description="Specific agent to assess. If omitted, runs org-wide assessment.",
    )


class ComplianceResultResponse(BaseModel):
    """Result of a single check within a report."""

    id: int
    check_id: int
    check: ComplianceCheckResponse
    status: str = Field(description="pass, fail, warning, not_applicable, not_evaluated")
    evidence: dict | None = Field(None, description="What was checked and found")
    remediation: str | None = Field(None, description="How to fix if failed")

    model_config = {"from_attributes": True}


class ComplianceReportResponse(BaseModel):
    """A compliance assessment report with results."""

    id: int
    user_id: uuid.UUID
    framework_id: int
    framework_name: str | None = None
    agent_id: uuid.UUID | None = None
    status: str = Field(description="running, completed, failed")
    score: float | None = Field(None, description="Compliance score 0-100")
    summary: str | None = None
    results: list[ComplianceResultResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceReportListResponse(BaseModel):
    """List of compliance reports."""

    items: list[ComplianceReportResponse]
    total: int


# ── Status Summary ───────────────────────────────────────────────────


class ComplianceStatusResponse(BaseModel):
    """Overall compliance posture summary."""

    overall_score: float | None = Field(None, description="Average score across latest reports")
    frameworks_assessed: int = 0
    total_checks: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    checks_warning: int = 0
    critical_failures: list[dict] = Field(
        default_factory=list,
        description="List of critical/high severity failures needing attention",
    )
    latest_reports: list[ComplianceReportResponse] = []
