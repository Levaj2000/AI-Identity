"""SOC 2 TSC 2017 profile builder.

Produces the full SOC 2 Type II evidence set per
``docs/compliance/export-profiles.md`` §SOC 2. The builder is
deterministic given fixed inputs — every row order is pinned to
``id ASC`` or ``created_at ASC`` so re-running a build produces
byte-identical artifact contents (signatures will differ due to
ECDSA nonce; that's expected).

Control mapping (per the scoping doc):

| Artifact | Controls |
|---|---|
| ``access_log.csv`` | CC6.1, CC7.2 |
| ``change_log.csv`` | CC6.2, CC6.6, CC8.1 |
| ``attestations/*.dsse.json`` | CC7.2 |
| ``chain_integrity.json`` | CC7.2 |
| ``control_results.csv`` | CC6.3, CC6.7, CC9.1 |
| ``agent_inventory.csv`` | — (informational, aids sampling) |
| ``policy_snapshots/*.json`` | CC8.1 |

CC7.3 incident records are flagged as a known gap in the scoping doc
and tracked under the ``IncidentRecord`` model sprint item; not
produced here.
"""

from __future__ import annotations

import csv
import datetime  # noqa: TC003 — runtime use in _rfc3339
import io
import json
import uuid  # noqa: TC003 — runtime use (str(id), etc.)

from sqlalchemy.orm import Session  # noqa: TC002 — runtime db.query

from common.audit.writer import verify_chain
from common.compliance.bundle import (
    ComplianceExportBundle,  # noqa: TC001 — used at runtime via bundle.write_*
)
from common.models import (
    Agent,
    AuditLog,
    ComplianceReport,
    ComplianceResult,
    ForensicAttestation,
    OrgMembership,
    Policy,
)

# Action types the gateway/API writes into audit_log.request_metadata
# when an agent/key/policy lifecycle event happens. These are the
# canonical change events exported for CC6.2/CC6.6/CC8.1 evidence.
_LIFECYCLE_ACTIONS: frozenset[str] = frozenset(
    {
        "agent_created",
        "agent_updated",
        "agent_revoked",
        "key_created",
        "key_rotated",
        "key_revoked",
        "policy_created",
        "policy_updated",
        "policy_deleted",
    }
)


# ── Top-level entrypoint ─────────────────────────────────────────────


def build_soc2_bundle(
    bundle: ComplianceExportBundle,
    *,
    db: Session,
    org_id: uuid.UUID,
    export_id: uuid.UUID,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
    built_at: datetime.datetime,
    agent_ids: list[uuid.UUID] | None,
) -> None:
    """Populate ``bundle`` with the full SOC 2 TSC 2017 evidence set.

    Caller is responsible for sealing the bundle — this function only
    writes content. Keeping seal out here means the orchestrator can
    add guardrail facts or cross-artifact summaries before sealing.

    ``agent_ids`` narrows the export to a sampling-plan subset; null
    means whole-org. Every query below honors this filter so an
    auditor targeting a handful of agents doesn't get the firehose.
    """
    scope_agent_ids = _resolve_scope(db, org_id=org_id, agent_ids=agent_ids)

    agent_count = _write_agent_inventory(bundle, db, org_id=org_id, scope_agent_ids=scope_agent_ids)
    access_count = _write_access_log(
        bundle,
        db,
        org_id=org_id,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    change_count = _write_change_log(
        bundle,
        db,
        org_id=org_id,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    attestation_count = _write_attestations(
        bundle,
        db,
        org_id=org_id,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    chain_result = _write_chain_integrity(
        bundle,
        db,
        built_at=built_at,
    )
    control_result_count = _write_control_results(
        bundle,
        db,
        org_id=org_id,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    policy_count = _write_policy_snapshots(
        bundle,
        db,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )

    # Meta-artifact: cross-references counts, control mappings, and
    # scope facts so an auditor can see at a glance what's in the
    # archive and which TSC criteria each file supports.
    _write_evidence_summary(
        bundle,
        export_id=export_id,
        org_id=org_id,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
        built_at=built_at,
        agent_ids=agent_ids,
        counts={
            "agent_inventory": agent_count,
            "access_log": access_count,
            "change_log": change_count,
            "attestations": attestation_count,
            "control_results": control_result_count,
            "policy_snapshots": policy_count,
        },
        chain_integrity={
            "valid": chain_result["valid"],
            "total_entries": chain_result["total_entries"],
            "entries_verified": chain_result["entries_verified"],
        },
    )


# ── Scope resolution ─────────────────────────────────────────────────


def _resolve_scope(
    db: Session,
    *,
    org_id: uuid.UUID,
    agent_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    """Resolve the list of agent ids this export covers.

    ``agent_ids=None`` → every agent currently belonging to the org
    (including revoked, since SOC 2 Type II covers a period during
    which revoked agents were still active for part of it).
    Otherwise, we trust the caller — the router already verified
    every id belongs to ``org_id``.
    """
    if agent_ids is not None:
        return list(agent_ids)
    rows = db.query(Agent.id).filter(Agent.org_id == org_id).order_by(Agent.id.asc()).all()
    return [r[0] for r in rows]


# ── Artifact writers ─────────────────────────────────────────────────


def _write_agent_inventory(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
) -> int:
    """Every agent in scope with its lifecycle columns. Useful for
    sampling-plan evidence and SOC 2 Section III narrative support.
    """
    query = db.query(Agent).filter(Agent.org_id == org_id)
    if scope_agent_ids:
        query = query.filter(Agent.id.in_(scope_agent_ids))
    agents = query.order_by(Agent.id.asc()).all()

    rows = [
        {
            "agent_id": str(a.id),
            "name": a.name,
            "status": a.status,
            "created_at": _rfc3339(a.created_at),
            "updated_at": _rfc3339(a.updated_at),
            "revoked_at": _rfc3339(a.revoked_at) if a.revoked_at else "",
            "user_id": str(a.user_id) if a.user_id else "",
            "org_id": str(a.org_id) if a.org_id else "",
            "eu_ai_act_risk_class": a.eu_ai_act_risk_class or "",
        }
        for a in agents
    ]
    _write_csv(
        bundle,
        path="agent_inventory.csv",
        fieldnames=[
            "agent_id",
            "name",
            "status",
            "created_at",
            "updated_at",
            "revoked_at",
            "user_id",
            "org_id",
            "eu_ai_act_risk_class",
        ],
        rows=rows,
        controls=[],
    )
    return len(rows)


def _write_access_log(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Every audit_log row for the scope + period. CC6.1 + CC7.2.

    policy_version is extracted from request_metadata when present;
    the column is left blank otherwise so an auditor doesn't see a
    fabricated version for requests that predate policy versioning.
    """
    query = (
        db.query(AuditLog)
        .filter(
            AuditLog.org_id == org_id,
            AuditLog.created_at >= audit_period_start,
            AuditLog.created_at <= audit_period_end,
        )
        .order_by(AuditLog.id.asc())
    )
    if scope_agent_ids:
        query = query.filter(AuditLog.agent_id.in_(scope_agent_ids))

    rows = []
    for entry in query.all():
        metadata = entry.request_metadata or {}
        rows.append(
            {
                "id": entry.id,
                "created_at": _rfc3339(entry.created_at),
                "agent_id": str(entry.agent_id) if entry.agent_id else "",
                "org_id": str(entry.org_id) if entry.org_id else "",
                "user_id": str(entry.user_id) if entry.user_id else "",
                "endpoint": entry.endpoint,
                "method": entry.method,
                "decision": entry.decision,
                "policy_version": str(metadata.get("policy_version", "")),
                "correlation_id": entry.correlation_id or "",
                "entry_hash": entry.entry_hash,
                "prev_hash": entry.prev_hash,
            }
        )
    _write_csv(
        bundle,
        path="access_log.csv",
        fieldnames=[
            "id",
            "created_at",
            "agent_id",
            "org_id",
            "user_id",
            "endpoint",
            "method",
            "decision",
            "policy_version",
            "correlation_id",
            "entry_hash",
            "prev_hash",
        ],
        rows=rows,
        controls=["SOC2-CC6.1", "SOC2-CC7.2"],
    )
    return len(rows)


def _write_change_log(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Agent / policy / key lifecycle events. CC6.2, CC6.6, CC8.1.

    Reconstructed from audit_log by filtering ``request_metadata.action_type``
    against the canonical lifecycle set. That's the source of truth for
    who changed what and when — the live tables only show the current
    state, not the history.
    """
    query = (
        db.query(AuditLog)
        .filter(
            AuditLog.org_id == org_id,
            AuditLog.created_at >= audit_period_start,
            AuditLog.created_at <= audit_period_end,
        )
        .order_by(AuditLog.id.asc())
    )
    if scope_agent_ids:
        query = query.filter(AuditLog.agent_id.in_(scope_agent_ids))

    rows = []
    for entry in query.all():
        metadata = entry.request_metadata or {}
        action = metadata.get("action_type")
        if action not in _LIFECYCLE_ACTIONS:
            continue
        rows.append(
            {
                "audit_log_id": entry.id,
                "created_at": _rfc3339(entry.created_at),
                "action_type": action,
                "resource_type": metadata.get("resource_type", ""),
                "agent_id": str(entry.agent_id) if entry.agent_id else "",
                "agent_name": entry.agent_name or metadata.get("agent_name", ""),
                "actor_user_id": str(entry.user_id) if entry.user_id else "",
                "decision": entry.decision,
                "details_json": json.dumps(
                    {
                        k: v
                        for k, v in metadata.items()
                        if k not in {"action_type", "resource_type"}
                    },
                    sort_keys=True,
                ),
            }
        )
    _write_csv(
        bundle,
        path="change_log.csv",
        fieldnames=[
            "audit_log_id",
            "created_at",
            "action_type",
            "resource_type",
            "agent_id",
            "agent_name",
            "actor_user_id",
            "decision",
            "details_json",
        ],
        rows=rows,
        controls=["SOC2-CC6.2", "SOC2-CC6.6", "SOC2-CC8.1"],
    )
    return len(rows)


def _write_attestations(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """One file per forensic attestation signed during the period.

    The authoritative artifact is the DSSE envelope (``.envelope``
    JSONB column), so we just serialize it verbatim. The file name is
    ``<session_id>.dsse.json`` — matches the convention referenced in
    the ADR's Bundle structure diagram.

    Note: attestations are not narrowed by ``agent_ids`` because
    attestations are session-scoped, not agent-scoped (a session can
    include multiple agents' events). Auditors examining per-agent
    evidence can cross-reference via ``audit_log_ids`` inside the
    envelope payload.
    """
    attestations = (
        db.query(ForensicAttestation)
        .filter(
            ForensicAttestation.org_id == org_id,
            ForensicAttestation.signed_at >= audit_period_start,
            ForensicAttestation.signed_at <= audit_period_end,
        )
        .order_by(ForensicAttestation.signed_at.asc())
        .all()
    )
    for att in attestations:
        bundle.write_json(
            f"attestations/{att.session_id}.dsse.json",
            att.envelope,
            controls=["SOC2-CC7.2"],
        )
    return len(attestations)


def _write_chain_integrity(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    built_at: datetime.datetime,
) -> dict:
    """Verify the global audit chain at export time, write result.

    CC7.2 operating-effectiveness evidence. Note the verification is
    system-wide, not per-org — the HMAC chain is a global linkage per
    the writer's design. That gives a stronger statement than per-org
    verification would: "the whole audit log was tamper-free at
    export time," not just "this org's rows hashed correctly."
    """
    result = verify_chain(db)
    payload = {
        "verified_at": _rfc3339(built_at),
        "scope": "global",
        "valid": bool(result.valid),
        "total_entries": int(result.total_entries),
        "entries_verified": int(result.entries_verified),
        "first_broken_id": result.first_broken_id,
        "message": result.message or "",
    }
    bundle.write_json(
        "chain_integrity.json",
        payload,
        controls=["SOC2-CC7.2"],
    )
    return payload


def _write_control_results(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Automated compliance-check results for the period. CC6.3, CC6.7, CC9.1.

    Filters ``ComplianceReport`` by (report.user in org's users) and
    the period, then flattens each report's results into CSV rows.
    Scope narrowing by ``agent_ids`` is applied when the report
    targeted a specific agent.
    """
    # Resolve in-org user ids via OrgMembership rather than the
    # denormalized User.org_id field. Production schema drift: the
    # users.org_id column was created as VARCHAR in an early migration
    # but the model says UUID, so direct comparisons fail with
    # `operator does not exist: character varying = uuid`.
    # OrgMembership is UUID-correct, so going through the join table
    # works and is also semantically more accurate (active members of
    # an org, not stale denormalized pointers).
    org_user_ids = [
        m.user_id for m in db.query(OrgMembership).filter(OrgMembership.org_id == org_id).all()
    ]

    report_query = (
        db.query(ComplianceReport)
        .filter(
            ComplianceReport.user_id.in_(org_user_ids or [uuid.UUID(int=0)]),
            ComplianceReport.created_at >= audit_period_start,
            ComplianceReport.created_at <= audit_period_end,
        )
        .order_by(ComplianceReport.id.asc())
    )
    if scope_agent_ids:
        # Keep org-wide reports (agent_id is null) AND agent-specific
        # reports for agents in scope. Dropping the null bucket would
        # silently hide org-wide control evaluations from the export.
        report_query = report_query.filter(
            (ComplianceReport.agent_id.is_(None)) | (ComplianceReport.agent_id.in_(scope_agent_ids))
        )
    reports = report_query.all()

    rows: list[dict] = []
    for report in reports:
        results = (
            db.query(ComplianceResult)
            .filter(ComplianceResult.report_id == report.id)
            .order_by(ComplianceResult.id.asc())
            .all()
        )
        for result in results:
            rows.append(
                {
                    "report_id": report.id,
                    "report_created_at": _rfc3339(report.created_at),
                    "framework_id": report.framework_id,
                    "target_agent_id": str(report.agent_id) if report.agent_id else "",
                    "report_status": report.status,
                    "report_score": "" if report.score is None else str(report.score),
                    "check_id": result.check_id,
                    "check_status": result.status,
                    "remediation": result.remediation or "",
                    "evidence_json": json.dumps(result.evidence or {}, sort_keys=True),
                }
            )
    _write_csv(
        bundle,
        path="control_results.csv",
        fieldnames=[
            "report_id",
            "report_created_at",
            "framework_id",
            "target_agent_id",
            "report_status",
            "report_score",
            "check_id",
            "check_status",
            "remediation",
            "evidence_json",
        ],
        rows=rows,
        controls=["SOC2-CC6.3", "SOC2-CC6.7", "SOC2-CC9.1"],
    )
    return len(rows)


def _write_policy_snapshots(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Point-in-time policy rules for each change during the period.

    One file per ``Policy`` row with ``updated_at`` in-period. Gives
    CC8.1 evidence that policy changes were tracked with their exact
    rule content, not just "something changed."
    """
    if not scope_agent_ids:
        return 0
    policies = (
        db.query(Policy)
        .filter(
            Policy.agent_id.in_(scope_agent_ids),
            Policy.updated_at >= audit_period_start,
            Policy.updated_at <= audit_period_end,
        )
        .order_by(Policy.updated_at.asc(), Policy.id.asc())
        .all()
    )
    for policy in policies:
        timestamp = policy.updated_at.strftime("%Y%m%dT%H%M%SZ")
        # Tie-break with id so two policy rows updated in the same
        # second don't collide on path.
        path = f"policy_snapshots/{timestamp}_{policy.id}.json"
        bundle.write_json(
            path,
            {
                "policy_id": policy.id,
                "agent_id": str(policy.agent_id),
                "version": policy.version,
                "is_active": policy.is_active,
                "rules": policy.rules,
                "created_at": _rfc3339(policy.created_at),
                "updated_at": _rfc3339(policy.updated_at),
            },
            controls=["SOC2-CC8.1"],
        )
    return len(policies)


def _write_evidence_summary(
    bundle: ComplianceExportBundle,
    *,
    export_id: uuid.UUID,
    org_id: uuid.UUID,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
    built_at: datetime.datetime,
    agent_ids: list[uuid.UUID] | None,
    counts: dict[str, int],
    chain_integrity: dict,
) -> None:
    """Cross-reference of artifacts → TSC criteria + counts.

    Auditor-facing at-a-glance view. Not required by SOC 2 itself, but
    saves the auditor from having to open every file to understand
    scope.
    """
    bundle.write_json(
        "evidence_summary.json",
        {
            "profile": "soc2_tsc_2017",
            "export_id": str(export_id),
            "org_id": str(org_id),
            "audit_period_start": _rfc3339(audit_period_start),
            "audit_period_end": _rfc3339(audit_period_end),
            "built_at": _rfc3339(built_at),
            "scope": {
                "agent_ids": [str(a) for a in agent_ids] if agent_ids else None,
                "whole_org": agent_ids is None,
            },
            "counts": counts,
            "chain_integrity": chain_integrity,
            "artifact_control_mapping": {
                "agent_inventory.csv": [],
                "access_log.csv": ["SOC2-CC6.1", "SOC2-CC7.2"],
                "change_log.csv": ["SOC2-CC6.2", "SOC2-CC6.6", "SOC2-CC8.1"],
                "attestations/*.dsse.json": ["SOC2-CC7.2"],
                "chain_integrity.json": ["SOC2-CC7.2"],
                "control_results.csv": ["SOC2-CC6.3", "SOC2-CC6.7", "SOC2-CC9.1"],
                "policy_snapshots/*.json": ["SOC2-CC8.1"],
            },
            "known_gaps": [
                "CC7.3 incident records: no IncidentRecord model yet — "
                "postmortems live as markdown in docs/incident-response/ "
                "and are not included in this export.",
            ],
        },
        controls=[],
    )


# ── Helpers ─────────────────────────────────────────────────────────


def _write_csv(
    bundle: ComplianceExportBundle,
    *,
    path: str,
    fieldnames: list[str],
    rows: list[dict],
    controls: list[str],
) -> None:
    """Serialize rows to RFC 4180 CSV and add to the bundle.

    Always writes the header row even if ``rows`` is empty — auditor
    tooling expects a schema even for zero-row periods, and manifest
    hashing works the same either way.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    bundle.write_text(path, buf.getvalue(), controls=controls)


def _rfc3339(value: datetime.datetime) -> str:
    """ISO 8601 / RFC 3339 with explicit UTC ``Z`` suffix.

    Matches the cross-cutting format decision in
    ``docs/compliance/export-profiles.md`` — no local-time fields
    anywhere in the export.
    """
    if value.tzinfo is None:
        utc = value.replace(tzinfo=datetime.UTC)
    else:
        utc = value.astimezone(datetime.UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["build_soc2_bundle"]
