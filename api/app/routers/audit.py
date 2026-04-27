"""Audit log endpoints — read-only access, integrity verification, and AI Forensics.

The audit log is append-only with an HMAC integrity chain. These endpoints
provide read access (scoped to the authenticated user's agents), chain
verification for SOC 2 compliance, and forensics features for incident
reconstruction and reporting.
"""

import csv
import io
import logging
import pathlib
import uuid
import zipfile
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.audit import generate_report_signature, verify_chain
from common.models import Agent, AuditLog, OrgMembership, Policy, User, get_db
from common.schemas.agent import (
    AuditChainVerifyResponse,
    AuditLogListResponse,
    AuditLogResponse,
    AuditReconstructResponse,
    AuditStatsResponse,
    AuditSummaryRequest,
    AuditSummaryResponse,
    ForensicsReportResponse,
    PolicyResponse,
    TopEndpoint,
)

logger = logging.getLogger("ai_identity.api.audit")

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# ── Helper: get user's agent IDs ────────────────────────────────────


def _user_agent_ids(db: Session, user: User) -> list[uuid.UUID]:
    """Return list of agent IDs owned by the user."""
    return [row[0] for row in db.query(Agent.id).filter(Agent.user_id == user.id).all()]


def _is_org_admin(db: Session, user: User, org_id: uuid.UUID) -> bool:
    """True if the user is an owner or admin in the given org.

    Platform admins (user.role == 'admin') also pass. Used to gate access
    to org-wide audit views where a single member can read every agent's
    activity in their tenant.
    """
    if user.role == "admin":
        return True
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.role.in_(("owner", "admin")),
        )
        .first()
    )
    return membership is not None


def _normalize_decision(decision: str | None) -> str | None:
    """Map long-form API values ("allowed"/"denied") to short form stored in DB ("allow"/"deny")."""
    _map = {"allowed": "allow", "denied": "deny"}
    return _map.get(decision, decision) if decision else decision


def _build_audit_query(
    db: Session,
    user_agent_ids: list[uuid.UUID],
    agent_id: uuid.UUID | None = None,
    decision: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    endpoint: str | None = None,
    action_type: str | None = None,
    model: str | None = None,
    cost_min: float | None = None,
    cost_max: float | None = None,
    user_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
):
    """Build a filtered audit log query scoped to user's agents.

    Also includes shadow agent entries (denied requests where audit_log.user_id
    matches the current user) so the Forensics page can display them.
    """
    from sqlalchemy import or_

    decision = _normalize_decision(decision)

    # Base scope: entries for registered agents OR entries owned by this user
    # (shadow agent denials from inactive agents have user_id set)
    # OR denied entries for a specific unregistered agent_id (shadow agents)
    if user_id:
        query = db.query(AuditLog).filter(
            or_(
                AuditLog.agent_id.in_(user_agent_ids),
                AuditLog.user_id == user_id,
            )
        )
    else:
        query = db.query(AuditLog).filter(AuditLog.agent_id.in_(user_agent_ids))

    if agent_id:
        if agent_id in user_agent_ids:
            # Registered agent — filter normally
            query = query.filter(AuditLog.agent_id == agent_id)
        else:
            # Unregistered agent (shadow agent) — query denied entries directly
            # This is safe: denied shadow entries contain no sensitive data
            query = db.query(AuditLog).filter(
                AuditLog.agent_id == agent_id,
                AuditLog.decision == "deny",
            )

    if decision:
        query = query.filter(AuditLog.decision == decision)

    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)

    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    if endpoint:
        query = query.filter(AuditLog.endpoint.ilike(f"%{endpoint}%"))

    if action_type:
        # Filter by action_type inside JSONB request_metadata
        query = query.filter(AuditLog.request_metadata["action_type"].astext == action_type)

    if model:
        query = query.filter(AuditLog.request_metadata["model"].astext == model)

    if cost_min is not None:
        query = query.filter(AuditLog.cost_estimate_usd >= cost_min)

    if cost_max is not None:
        query = query.filter(AuditLog.cost_estimate_usd <= cost_max)

    if correlation_id:
        query = query.filter(AuditLog.correlation_id == correlation_id)

    return query


def _compute_stats(
    db: Session,
    user_agent_ids: list[uuid.UUID],
    agent_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    user_id: uuid.UUID | None = None,
) -> AuditStatsResponse:
    """Compute aggregated statistics for a filtered audit window."""
    from sqlalchemy import or_

    if user_id:
        base = db.query(AuditLog).filter(
            or_(AuditLog.agent_id.in_(user_agent_ids), AuditLog.user_id == user_id)
        )
    else:
        base = db.query(AuditLog).filter(AuditLog.agent_id.in_(user_agent_ids))

    if agent_id:
        if agent_id in user_agent_ids:
            base = base.filter(AuditLog.agent_id == agent_id)
        else:
            # Shadow agent — query denied entries directly
            base = db.query(AuditLog).filter(
                AuditLog.agent_id == agent_id,
                AuditLog.decision == "deny",
            )
    if start_date:
        base = base.filter(AuditLog.created_at >= start_date)
    if end_date:
        base = base.filter(AuditLog.created_at <= end_date)

    # Decision counts
    decision_counts = (
        base.with_entities(AuditLog.decision, func.count(AuditLog.id))
        .group_by(AuditLog.decision)
        .all()
    )
    counts = {d: c for d, c in decision_counts}

    # Aggregates
    agg = base.with_entities(
        func.count(AuditLog.id),
        func.coalesce(func.sum(AuditLog.cost_estimate_usd), 0),
        func.avg(AuditLog.latency_ms),
    ).first()

    total_events = agg[0] if agg else 0
    total_cost = float(agg[1]) if agg else 0.0
    avg_latency = round(float(agg[2]), 1) if agg and agg[2] is not None else None

    # Top endpoints
    top_eps = (
        base.with_entities(AuditLog.endpoint, func.count(AuditLog.id).label("cnt"))
        .group_by(AuditLog.endpoint)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )

    return AuditStatsResponse(
        total_events=total_events,
        allowed_count=counts.get("allow", 0) + counts.get("allowed", 0),
        denied_count=counts.get("deny", 0) + counts.get("denied", 0),
        error_count=counts.get("error", 0),
        total_cost_usd=total_cost,
        avg_latency_ms=avg_latency,
        top_endpoints=[TopEndpoint(endpoint=ep, count=cnt) for ep, cnt in top_eps],
    )


# ── User Endpoints ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit log entries",
    response_description="Paginated audit log entries, newest first",
)
def list_audit_logs(
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    decision: str | None = Query(None, pattern="^(allowed|denied|error)$"),
    start_date: datetime | None = Query(None, description="Filter entries after this timestamp"),
    end_date: datetime | None = Query(None, description="Filter entries before this timestamp"),
    endpoint: str | None = Query(None, description="Filter by endpoint (partial match)"),
    action_type: str | None = Query(None, description="Filter by metadata action_type"),
    model: str | None = Query(None, description="Filter by metadata model"),
    cost_min: float | None = Query(None, description="Minimum cost_estimate_usd"),
    cost_max: float | None = Query(None, description="Maximum cost_estimate_usd"),
    correlation_id: str | None = Query(
        None,
        max_length=64,
        description=(
            "Filter to events sharing this correlation ID — use when tracing "
            "a single request across services."
        ),
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit log entries with optional filters.

    Scoping rules (most-to-least privileged):
      1. Org owner/admin → all entries in their org (every agent, every member).
      2. Regular user    → entries for agents they own, plus their own
         shadow-agent denials (unregistered agent_ids tagged with their user_id).

    Supports filtering by agent, decision, date range, endpoint,
    metadata action_type, metadata model, and cost range.
    """
    decision = _normalize_decision(decision)
    # Org owners/admins get org-wide visibility via the fast org_id index.
    # Uses denormalized audit_log.org_id (populated at write time) so the
    # query stays flat even at 100+ agents in the org.
    if user.org_id and _is_org_admin(db, user, user.org_id):
        query = db.query(AuditLog).filter(AuditLog.org_id == user.org_id)

        if agent_id:
            query = query.filter(AuditLog.agent_id == agent_id)
        if decision:
            query = query.filter(AuditLog.decision == decision)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        if endpoint:
            query = query.filter(AuditLog.endpoint.ilike(f"%{endpoint}%"))
        if action_type:
            query = query.filter(AuditLog.request_metadata["action_type"].astext == action_type)
        if model:
            query = query.filter(AuditLog.request_metadata["model"].astext == model)
        if cost_min is not None:
            query = query.filter(AuditLog.cost_estimate_usd >= cost_min)
        if cost_max is not None:
            query = query.filter(AuditLog.cost_estimate_usd <= cost_max)
        if correlation_id:
            query = query.filter(AuditLog.correlation_id == correlation_id)
    else:
        user_agents = _user_agent_ids(db, user)
        query = _build_audit_query(
            db,
            user_agents,
            agent_id=agent_id,
            decision=decision,
            start_date=start_date,
            end_date=end_date,
            endpoint=endpoint,
            action_type=action_type,
            model=model,
            cost_min=cost_min,
            cost_max=cost_max,
            user_id=user.id,
            correlation_id=correlation_id,
        )

    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── Forensics Endpoints (must be before /verify and /admin) ─────────


@router.get(
    "/stats",
    response_model=AuditStatsResponse,
    summary="Aggregated audit statistics",
    response_description="Decision counts, cost totals, top endpoints",
    tags=["forensics"],
)
def audit_stats(
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    start_date: datetime | None = Query(None, description="Window start"),
    end_date: datetime | None = Query(None, description="Window end"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregated statistics for audit log entries.

    Provides decision counts, cost totals, average latency, and top
    endpoints for the given time window. Scoped to user's agents.
    """
    user_agents = _user_agent_ids(db, user)

    return _compute_stats(
        db,
        user_agents,
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user.id,
    )


# ── AI Summary (Perplexity) ────────────────────────────────────────

# Simple in-memory rate limiter: {user_id: [timestamps]}
_summary_rate_limit: dict[uuid.UUID, list[datetime]] = {}


def _check_summary_rate_limit(user_id: uuid.UUID, tier: str) -> None:
    """Enforce per-user hourly rate limits on AI summaries."""
    limit = 5 if tier == "pro" else 20  # business / enterprise get 20
    now = datetime.now(UTC)
    window = [t for t in _summary_rate_limit.get(user_id, []) if (now - t).total_seconds() < 3600]
    if len(window) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {limit} AI summaries per hour. Try again later.",
        )
    window.append(now)
    _summary_rate_limit[user_id] = window


@router.post(
    "/summarize",
    response_model=AuditSummaryResponse,
    summary="AI-powered audit summary",
    response_description="Natural-language summary of agent activity",
    tags=["forensics"],
)
def audit_summarize(
    body: AuditSummaryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI-powered summary of audit log events.

    Uses the Perplexity API to produce a natural-language explanation of
    agent activity including anomalies, concerns, and recommendations.
    Requires a Pro or higher subscription tier.
    """
    from api.app.services.perplexity import PerplexityError, summarize_audit_events
    from common.config.settings import settings as app_settings

    # ── Tier gate ──────────────────────────────────────────────────
    if user.tier == "free":
        raise HTTPException(
            status_code=403,
            detail="AI Summaries require a Pro or higher plan.",
        )

    # ── Feature gate ───────────────────────────────────────────────
    if not app_settings.perplexity_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI Summary feature is not configured.",
        )

    # ── Rate limit ─────────────────────────────────────────────────
    _check_summary_rate_limit(user.id, user.tier)

    # ── Query events ───────────────────────────────────────────────
    user_agents = _user_agent_ids(db, user)

    if body.event_ids:
        # Specific events, still scoped to user's agents
        query = _build_audit_query(db, user_agents, user_id=user.id)
        query = query.filter(AuditLog.id.in_(body.event_ids))
    else:
        query = _build_audit_query(
            db,
            user_agents,
            agent_id=body.agent_id,
            decision=body.decision,
            start_date=body.start_date,
            end_date=body.end_date,
            endpoint=body.endpoint,
            action_type=body.action_type,
            model=body.model,
            cost_min=body.cost_min,
            cost_max=body.cost_max,
            user_id=user.id,
        )

    entries = query.order_by(AuditLog.created_at.asc()).limit(body.max_events).all()

    if not entries:
        raise HTTPException(
            status_code=400,
            detail="No audit events found for the given criteria.",
        )

    # ── Resolve agent names ────────────────────────────────────────
    agent_ids_in_results = {e.agent_id for e in entries}
    agent_names: dict[uuid.UUID, str] = {}
    if agent_ids_in_results:
        rows = db.query(Agent.id, Agent.name).filter(Agent.id.in_(agent_ids_in_results)).all()
        agent_names = {row[0]: row[1] for row in rows}

    # ── Compute stats ────────────────────────────────────────────────
    stats = _compute_stats(
        db,
        user_agents,
        agent_id=body.agent_id,
        start_date=body.start_date,
        end_date=body.end_date,
        user_id=user.id,
    )

    # ── Build normalized event data for structured prompt ──────────
    # Per-event details (compact for prompt context)
    event_details = []
    for e in entries:
        name = agent_names.get(e.agent_id, str(e.agent_id)[:8])
        meta = e.request_metadata if isinstance(e.request_metadata, dict) else {}
        event_details.append(
            {
                "timestamp": e.created_at.isoformat(),
                "agent_name": meta.get("agent_name", name),
                "agent_id": str(e.agent_id),
                "http_method": e.method or "",
                "endpoint": e.endpoint or "",
                "decision": e.decision,
                "cost_usd": float(e.cost_estimate_usd) if e.cost_estimate_usd else 0,
                "latency_ms": e.latency_ms,
                "action_type": meta.get("action_type", ""),
                "resource_type": meta.get("resource_type", ""),
                "status_before": meta.get("old_status", ""),
                "status_after": meta.get("new_status", ""),
                "deny_reason": meta.get("deny_reason", ""),
                "keys_revoked": meta.get("keys_revoked", ""),
                "model": meta.get("model", ""),
            }
        )

    # Determine time window
    window_start = (
        body.start_date.isoformat() if body.start_date else entries[0].created_at.isoformat()
    )
    window_end = body.end_date.isoformat() if body.end_date else entries[-1].created_at.isoformat()

    # Build notes for context
    notes_parts = []
    if len(entries) == 1:
        notes_parts.append("Single event in selected time window")
    if stats.denied_count > 0:
        notes_parts.append(f"{stats.denied_count} denied requests require review")
    if stats.error_count > 0:
        notes_parts.append(f"{stats.error_count} errors detected")

    event_data = {
        "time_window_start": window_start,
        "time_window_end": window_end,
        "requests_total": stats.total_events,
        "requests_allowed": stats.allowed_count,
        "requests_denied": stats.denied_count,
        "errors": stats.error_count,
        "cost_usd": float(stats.total_cost_usd),
        "avg_latency_ms": stats.avg_latency_ms,
        "supporting_events_count": len(entries),
        "events": event_details,
        "notes": "; ".join(notes_parts) if notes_parts else "No additional notes",
    }
    if body.focus_hint:
        event_data["analyst_focus"] = body.focus_hint

    # ── Call Perplexity ────────────────────────────────────────────
    try:
        report = summarize_audit_events(event_data=event_data)
    except PerplexityError as exc:
        status = 504 if "timed out" in str(exc) else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    # ── Apply guardrails ──────────────────────────────────────────
    # Force confidence down for single-event windows
    confidence = report.get("confidence", "medium")
    if len(entries) <= 1 and confidence == "high":
        report_risk = report.get("risk_level", "informational")
        if report_risk not in ("informational",):
            confidence = "medium"

    # Elevate risk if denials or errors present
    risk_level = report.get("risk_level", "informational")
    if stats.denied_count > 0 and risk_level == "informational":
        risk_level = "low"
    if stats.error_count > 0 and risk_level in ("informational", "low"):
        risk_level = "medium"

    return AuditSummaryResponse(
        title=report.get("title", "AI Agent Audit Summary"),
        executive_summary=report.get("executive_summary", ""),
        observed_facts=[
            {"label": f["label"], "value": f["value"]}
            for f in report.get("observed_facts", [])
            if isinstance(f, dict) and "label" in f and "value" in f
        ],
        assessment=report.get("assessment", ""),
        recommended_follow_ups=report.get("recommended_follow_ups", []),
        risk_level=risk_level,
        confidence=confidence,
        events_analyzed=len(entries),
        model_used=app_settings.perplexity_model,
        generated_at=datetime.now(UTC),
    )


@router.get(
    "/reconstruct",
    response_model=AuditReconstructResponse,
    summary="Incident reconstruction",
    response_description="Full event chain with policy context and chain verification",
    tags=["forensics"],
)
def audit_reconstruct(
    agent_id: uuid.UUID = Query(..., description="Agent to investigate"),
    start_date: datetime = Query(..., description="Investigation window start"),
    end_date: datetime = Query(..., description="Investigation window end"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reconstruct an incident: all events, active policy, and chain integrity.

    Returns the complete decision history for an agent within a time window,
    along with the policy that was active and cryptographic chain verification.
    """
    user_agents = _user_agent_ids(db, user)

    # Verify agent ownership
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get events in window
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.agent_id == agent_id,
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )

    # Chain verification for this agent
    chain_result = verify_chain(db, agent_id=agent_id)

    # Active policy
    active_policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )

    # Stats for window
    stats = _compute_stats(
        db, user_agents, agent_id=agent_id, start_date=start_date, end_date=end_date
    )

    return AuditReconstructResponse(
        agent_id=agent_id,
        agent_name=agent.name,
        start_date=start_date,
        end_date=end_date,
        events=[AuditLogResponse.model_validate(e) for e in events],
        chain_verification=AuditChainVerifyResponse(
            valid=chain_result.valid,
            total_entries=chain_result.total_entries,
            entries_verified=chain_result.entries_verified,
            first_broken_id=chain_result.first_broken_id,
            message=chain_result.message,
        ),
        active_policy=PolicyResponse.model_validate(active_policy) if active_policy else None,
        stats=stats,
    )


@router.get(
    "/report",
    summary="Generate forensics report",
    response_description="Forensics report with chain-of-custody certificate",
    tags=["forensics"],
)
def audit_report(
    agent_id: uuid.UUID = Query(..., description="Agent to report on"),
    start_date: datetime = Query(..., description="Report window start"),
    end_date: datetime = Query(..., description="Report window end"),
    format: str = Query("json", pattern="^(json|csv)$", description="Output format"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an exportable forensics report.

    JSON format includes a chain-of-custody verification certificate.
    CSV format provides a flat event table for external analysis.
    """
    user_agents = _user_agent_ids(db, user)

    # Verify agent ownership
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get events
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.agent_id == agent_id,
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )

    # Chain verification
    chain_result = verify_chain(db, agent_id=agent_id)

    # Active policy
    active_policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )

    # Stats
    stats = _compute_stats(
        db, user_agents, agent_id=agent_id, start_date=start_date, end_date=end_date
    )

    event_responses = [AuditLogResponse.model_validate(e) for e in events]

    if format == "csv":
        # Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "agent_id",
                "endpoint",
                "method",
                "decision",
                "cost_estimate_usd",
                "latency_ms",
                "created_at",
                "entry_hash",
                "prev_hash",
                "request_metadata",
            ]
        )
        for e in event_responses:
            writer.writerow(
                [
                    e.id,
                    str(e.agent_id),
                    e.endpoint,
                    e.method,
                    e.decision,
                    e.cost_estimate_usd,
                    e.latency_ms,
                    e.created_at.isoformat(),
                    e.entry_hash,
                    e.prev_hash,
                    str(e.request_metadata),
                ]
            )

        # Add chain verification and report signature as footer
        report_generated_at = datetime.now(tz=UTC)
        report_sig = generate_report_signature(
            report_id=f"fr-{agent_id.hex[:8]}-{start_date.strftime('%Y%m%d%H%M')}",
            generated_at=report_generated_at,
            chain_valid=chain_result.valid,
            total_entries=chain_result.total_entries,
            entries_verified=chain_result.entries_verified,
        )
        writer.writerow([])
        writer.writerow(["# Chain-of-Custody Certificate"])
        writer.writerow(["chain_valid", chain_result.valid])
        writer.writerow(["total_entries", chain_result.total_entries])
        writer.writerow(["entries_verified", chain_result.entries_verified])
        writer.writerow(["verification_message", chain_result.message])
        writer.writerow(["generated_at", report_generated_at.isoformat()])
        writer.writerow(["report_signature", report_sig])

        output.seek(0)
        filename = f"forensics-{agent.name}-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # JSON format
    report_id = f"fr-{agent_id.hex[:8]}-{start_date.strftime('%Y%m%d%H%M')}"
    report_generated_at = datetime.now(tz=UTC)
    chain_verify = AuditChainVerifyResponse(
        valid=chain_result.valid,
        total_entries=chain_result.total_entries,
        entries_verified=chain_result.entries_verified,
        first_broken_id=chain_result.first_broken_id,
        message=chain_result.message,
    )
    report_sig = generate_report_signature(
        report_id=report_id,
        generated_at=report_generated_at,
        chain_valid=chain_result.valid,
        total_entries=chain_result.total_entries,
        entries_verified=chain_result.entries_verified,
    )

    return ForensicsReportResponse(
        report_id=report_id,
        generated_at=report_generated_at,
        agent={
            "id": str(agent.id),
            "name": agent.name,
            "status": agent.status.value if hasattr(agent.status, "value") else str(agent.status),
            "description": agent.description,
        },
        time_window={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        events=event_responses,
        chain_verification=chain_verify,
        active_policy=PolicyResponse.model_validate(active_policy) if active_policy else None,
        stats=stats,
        report_signature=report_sig,
    )


# ── Verification Bundle ────────────────────────────────────────────

_BUNDLE_README = """\
# AI Identity — Forensic Report Verification

This bundle contains a forensic audit report from AI Identity and a tool to independently verify its integrity.

## What's Inside

- `forensics-report-*.json` — The signed forensic audit report
- `ai_identity_verify.py` — Standalone verification tool (Python 3.9+, no dependencies)

## Quick Start

1. Get your HMAC verification key from your AI Identity administrator
2. Open a terminal and run:

   export AI_IDENTITY_HMAC_KEY="your-key-here"
   python3 ai_identity_verify.py report forensics-report-*.json

3. You should see:

   Signature: VALID ✓

To also verify the full audit chain:

   python3 ai_identity_verify.py chain forensics-report-*.json

## What This Proves

- **Signature VALID**: The report data is authentic and has not been modified since export
- **Chain INTACT**: Every audit log entry links cryptographically to the previous one — no entries were inserted, deleted, or altered

## Need Help?

Contact your AI Identity administrator or visit https://ai-identity.co/docs
"""

# Resolve the CLI script path relative to the project root
_CLI_SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[3] / "cli" / "ai_identity_verify.py"


@router.get(
    "/report/bundle",
    summary="Download verification bundle",
    response_description="ZIP file with signed report, verification CLI, and README",
    tags=["forensics"],
)
def audit_report_bundle(
    agent_id: uuid.UUID = Query(..., description="Agent to report on"),
    start_date: datetime = Query(..., description="Report window start"),
    end_date: datetime = Query(..., description="Report window end"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download a ZIP bundle containing the signed forensics report, the standalone
    verification CLI script, and a client-facing README with instructions.
    """
    # Verify agent ownership
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Generate the full signed report (reuse the same logic as /report)
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.agent_id == agent_id,
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )

    chain_result = verify_chain(db, agent_id=agent_id)

    active_policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )

    user_agents = _user_agent_ids(db, user)
    stats = _compute_stats(
        db, user_agents, agent_id=agent_id, start_date=start_date, end_date=end_date
    )

    event_responses = [AuditLogResponse.model_validate(e) for e in events]

    report_id = f"fr-{agent_id.hex[:8]}-{start_date.strftime('%Y%m%d%H%M')}"
    report_generated_at = datetime.now(tz=UTC)
    chain_verify = AuditChainVerifyResponse(
        valid=chain_result.valid,
        total_entries=chain_result.total_entries,
        entries_verified=chain_result.entries_verified,
        first_broken_id=chain_result.first_broken_id,
        message=chain_result.message,
    )
    report_sig = generate_report_signature(
        report_id=report_id,
        generated_at=report_generated_at,
        chain_valid=chain_result.valid,
        total_entries=chain_result.total_entries,
        entries_verified=chain_result.entries_verified,
    )

    report = ForensicsReportResponse(
        report_id=report_id,
        generated_at=report_generated_at,
        agent={
            "id": str(agent.id),
            "name": agent.name,
            "status": agent.status.value if hasattr(agent.status, "value") else str(agent.status),
            "description": agent.description,
        },
        time_window={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        events=event_responses,
        chain_verification=chain_verify,
        active_policy=PolicyResponse.model_validate(active_policy) if active_policy else None,
        stats=stats,
        report_signature=report_sig,
    )

    # Serialize report to JSON
    report_json = report.model_dump_json(indent=2)

    # Build the ZIP bundle
    date_str = report_generated_at.strftime("%Y-%m-%d")
    agent_short = agent_id.hex[:8]
    report_filename = f"forensics-report-{agent_short}-{date_str}.json"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(report_filename, report_json)

        # Include the CLI verification script from disk
        if _CLI_SCRIPT_PATH.exists():
            zf.write(_CLI_SCRIPT_PATH, "ai_identity_verify.py")
        else:
            logger.warning("CLI script not found at %s", _CLI_SCRIPT_PATH)

        zf.writestr("README.md", _BUNDLE_README)

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.getvalue()

    bundle_filename = f"ai-identity-verify-{agent_short}-{date_str}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{bundle_filename}"'},
    )


# ── Chain Verification ──────────────────────────────────────────────


@router.get(
    "/verify",
    response_model=AuditChainVerifyResponse,
    summary="Verify audit chain integrity",
    response_description="Chain verification result",
)
def verify_audit_chain(
    agent_id: uuid.UUID | None = Query(
        None,
        description="Verify hash integrity for a specific agent only (no chain linkage)",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify the HMAC integrity chain of the audit log.

    Walks all entries in order, recomputes each HMAC, and checks
    that prev_hash links are consistent. Reports the first break found.

    Without agent_id: verifies the full global chain.
    With agent_id: verifies hash integrity for that agent's entries only.
    """
    if agent_id:
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

    result = verify_chain(db, agent_id=agent_id)

    logger.info(
        "Chain verification: valid=%s, entries=%s, verified=%s",
        result.valid,
        result.total_entries,
        result.entries_verified,
    )

    return AuditChainVerifyResponse(
        valid=result.valid,
        total_entries=result.total_entries,
        entries_verified=result.entries_verified,
        first_broken_id=result.first_broken_id,
        message=result.message,
    )


# ── Admin Audit Endpoints ────────────────────────────────────────────


@router.get(
    "/admin",
    response_model=AuditLogListResponse,
    summary="[Org Admin] List audit entries for an organization",
    response_description="Paginated audit log scoped to one org",
)
def admin_list_audit_logs(
    org_id: uuid.UUID = Query(
        ...,
        description=(
            "Organization to list audit entries for. Caller must be an owner or "
            "admin in this org (or a platform admin)."
        ),
    ),
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent ID"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user ID"),
    decision: str | None = Query(None, pattern="^(allowed|denied|error)$"),
    action_type: str | None = Query(
        None,
        description="Filter by action_type in metadata (e.g. agent_created, key_rotated)",
    ),
    correlation_id: str | None = Query(
        None,
        max_length=64,
        description=(
            "Filter to events sharing this correlation ID — the canonical "
            "cross-service trace lookup."
        ),
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit log entries scoped to a single organization.

    Access is gated by org membership: the caller must be an owner or
    admin in the target org (platform admins are also allowed).
    Supports filtering by agent_id, user_id, decision, action_type,
    and correlation_id.
    """
    if not _is_org_admin(db, user, org_id):
        # Deliberately 403, not 404 — the org exists, the caller just
        # doesn't have the role. We don't want to leak org existence here
        # because any user can guess UUIDs, but the role requirement is
        # the real gate.
        raise HTTPException(
            status_code=403,
            detail="Owner or admin role in this organization is required",
        )

    decision = _normalize_decision(decision)
    query = db.query(AuditLog).filter(AuditLog.org_id == org_id)

    if agent_id:
        query = query.filter(AuditLog.agent_id == agent_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if decision:
        query = query.filter(AuditLog.decision == decision)
    if action_type:
        # Filter by action_type inside JSONB request_metadata
        query = query.filter(AuditLog.request_metadata["action_type"].astext == action_type)
    if correlation_id:
        query = query.filter(AuditLog.correlation_id == correlation_id)

    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )
