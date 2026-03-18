"""Usage aggregation — time-series and per-agent usage data from audit_log.

Aggregates gateway audit log entries into daily time series, per-agent
breakdowns, and billing period summaries. Powers the customer dashboard
and internal reporting.
"""

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import case, cast, func
from sqlalchemy.orm import Session
from sqlalchemy.types import Date

from common.models import Agent, AuditLog, User

logger = logging.getLogger("ai_identity.api.usage_aggregation")


def _period_dates(now: date, reset_day: int = 1) -> tuple[date, date]:
    """Calculate the current billing period start/end dates.

    The billing period runs from reset_day of the current month
    to reset_day of the next month.
    """
    year, month = now.year, now.month
    day = min(reset_day, 28)  # Cap at 28 to avoid month-end issues

    period_start = date(year, month, day)
    if now < period_start:
        # We're before the reset day — period started last month
        period_start = date(year - 1, 12, day) if month == 1 else date(year, month - 1, day)

    # Period ends on reset_day of next month
    start_month = period_start.month
    start_year = period_start.year
    if start_month == 12:
        period_end = date(start_year + 1, 1, day)
    else:
        period_end = date(start_year, start_month + 1, day)

    return period_start, period_end


def _aggregate_period(
    db: Session,
    user_id,
    start_date: date,
    end_date: date,
) -> dict:
    """Aggregate audit_log entries for a date range."""
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC)

    # Total counts by decision
    rows = (
        db.query(
            AuditLog.decision,
            func.count().label("cnt"),
        )
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at < end_dt,
        )
        .group_by(AuditLog.decision)
        .all()
    )

    counts = {"allow": 0, "deny": 0, "error": 0}
    for decision, cnt in rows:
        counts[decision] = cnt
    total = sum(counts.values())

    # Active agents (distinct agent_ids)
    active_agents = (
        db.query(func.count(func.distinct(AuditLog.agent_id)))
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at < end_dt,
        )
        .scalar()
    ) or 0

    # Daily request counts for peak/avg calculation
    daily_counts = (
        db.query(func.count().label("cnt"))
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at < end_dt,
        )
        .group_by(cast(AuditLog.created_at, Date))
        .all()
    )

    daily_values = [row.cnt for row in daily_counts]
    days_in_period = max((end_date - start_date).days, 1)

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_requests": total,
        "allowed": counts["allow"],
        "denied": counts["deny"],
        "errors": counts["error"],
        "active_agents": active_agents,
        "peak_daily_requests": max(daily_values) if daily_values else 0,
        "avg_daily_requests": round(total / days_in_period, 1),
    }


def get_daily_time_series(
    db: Session,
    user_id,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Return daily usage data points for a date range."""
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC)

    rows = (
        db.query(
            cast(AuditLog.created_at, Date).label("day"),
            func.count().label("total"),
            func.sum(case((AuditLog.decision == "allow", 1), else_=0)).label("allowed"),
            func.sum(case((AuditLog.decision == "deny", 1), else_=0)).label("denied"),
            func.sum(case((AuditLog.decision == "error", 1), else_=0)).label("errors"),
        )
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at < end_dt,
        )
        .group_by(cast(AuditLog.created_at, Date))
        .order_by(cast(AuditLog.created_at, Date))
        .all()
    )

    # Build a dict for quick lookup
    data_by_day = {}
    for row in rows:
        data_by_day[row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day)] = {
            "total_requests": row.total,
            "allowed": row.allowed or 0,
            "denied": row.denied or 0,
            "errors": row.errors or 0,
        }

    # Fill in missing days with zeros
    result = []
    current = start_date
    while current < end_date:
        day_str = current.isoformat()
        if day_str in data_by_day:
            result.append({"date": day_str, **data_by_day[day_str]})
        else:
            result.append(
                {
                    "date": day_str,
                    "total_requests": 0,
                    "allowed": 0,
                    "denied": 0,
                    "errors": 0,
                }
            )
        current += timedelta(days=1)

    return result


def get_agent_breakdown(
    db: Session,
    user_id,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Return per-agent usage breakdown for a date range."""
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC)

    rows = (
        db.query(
            AuditLog.agent_id,
            func.count().label("total"),
            func.sum(case((AuditLog.decision == "allow", 1), else_=0)).label("allowed"),
            func.sum(case((AuditLog.decision == "deny", 1), else_=0)).label("denied"),
            func.max(AuditLog.created_at).label("last_active"),
        )
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at < end_dt,
        )
        .group_by(AuditLog.agent_id)
        .order_by(func.count().desc())
        .all()
    )

    # Fetch agent names in one query
    agent_ids = [row.agent_id for row in rows]
    agents = {}
    if agent_ids:
        agent_rows = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
        agents = {a.id: a for a in agent_rows}

    result = []
    for row in rows:
        agent = agents.get(row.agent_id)
        result.append(
            {
                "agent_id": str(row.agent_id),
                "agent_name": agent.name if agent else "(deleted)",
                "agent_status": agent.status if agent else "revoked",
                "total_requests": row.total,
                "allowed": row.allowed or 0,
                "denied": row.denied or 0,
                "last_active": row.last_active,
            }
        )

    return result


def get_full_aggregation(db: Session, user: User) -> dict:
    """Build the complete usage aggregation response."""
    today = date.today()
    reset_day = user.usage_reset_day or 1

    # Current billing period
    period_start, period_end = _period_dates(today, reset_day)

    # Previous billing period
    if period_start.month == 1:
        prev_start = date(period_start.year - 1, 12, min(reset_day, 28))
    else:
        prev_start = date(period_start.year, period_start.month - 1, min(reset_day, 28))
    prev_end = period_start

    # Aggregate both periods
    current_summary = _aggregate_period(db, user.id, period_start, period_end)

    prev_summary = None
    prev_total = (
        db.query(func.count())
        .filter(
            AuditLog.user_id == user.id,
            AuditLog.created_at
            >= datetime(prev_start.year, prev_start.month, prev_start.day, tzinfo=UTC),
            AuditLog.created_at < datetime(prev_end.year, prev_end.month, prev_end.day, tzinfo=UTC),
        )
        .scalar()
    )
    if prev_total and prev_total > 0:
        prev_summary = _aggregate_period(db, user.id, prev_start, prev_end)

    # Daily time series for current period
    daily = get_daily_time_series(
        db, user.id, period_start, min(today + timedelta(days=1), period_end)
    )

    # Per-agent breakdown for current period
    by_agent = get_agent_breakdown(db, user.id, period_start, period_end)

    return {
        "tier": user.tier,
        "billing_period": current_summary,
        "previous_period": prev_summary,
        "daily": daily,
        "by_agent": by_agent,
    }
