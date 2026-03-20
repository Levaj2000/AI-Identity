"""Compliance models — frameworks, checks, reports, and results."""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.models.base import Base


class ComplianceFramework(Base):
    """A regulatory or best-practice framework (e.g., EU AI Act, NIST AI RMF)."""

    __tablename__ = "compliance_frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="regulatory"
    )  # regulatory, industry, internal

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    checks: Mapped[list["ComplianceCheck"]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )


class ComplianceCheck(Base):
    """An individual compliance check within a framework."""

    __tablename__ = "compliance_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    framework_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "NIST-GOV-01"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )  # critical, high, medium, low
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="governance"
    )  # governance, security, transparency, accountability
    check_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="automated"
    )  # automated, manual, hybrid
    check_query: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # internal identifier for automated evaluation

    # Relationships
    framework: Mapped["ComplianceFramework"] = relationship(back_populates="checks")


class ComplianceReport(Base):
    """A point-in-time compliance assessment against a framework."""

    __tablename__ = "compliance_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    framework_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # None = org-wide assessment, set = agent-specific

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running, completed, failed
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100 percentage
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    framework: Mapped["ComplianceFramework"] = relationship()
    results: Mapped[list["ComplianceResult"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ComplianceResult(Base):
    """Result of a single compliance check within a report."""

    __tablename__ = "compliance_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compliance_checks.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_evaluated"
    )  # pass, fail, warning, not_applicable, not_evaluated
    evidence: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # what was checked, raw data
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)  # how to fix if failed

    # Relationships
    report: Mapped["ComplianceReport"] = relationship(back_populates="results")
    check: Mapped["ComplianceCheck"] = relationship()
