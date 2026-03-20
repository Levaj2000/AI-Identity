"""QA Run model — persists automated QA checklist results and sign-offs."""

import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class QARun(Base):
    """A single execution of the 15-step E2E QA checklist."""

    __tablename__ = "qa_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Run metadata
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="passed")
    run_by: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="production")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Run mode: "admin" (existing account) or "onboarding" (fresh test client)
    mode: Mapped[str | None] = mapped_column(String(20), nullable=True, default="admin")

    # Full check results (JSONB array of check objects)
    results: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Sign-offs
    customer_signoff_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_signoff_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    customer_signoff_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    staff_signoff_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    staff_signoff_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    staff_signoff_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
