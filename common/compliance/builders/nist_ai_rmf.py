"""NIST AI RMF 1.0 profile builder.

Produces the full NIST AI Risk Management Framework (AI RMF 1.0)
evidence set per ``docs/compliance/export-profiles.md`` §"NIST AI RMF
profile". Unlike SOC 2 + EU AI Act, AI RMF is **guidance not
regulation** — US federal contractors increasingly require it but
there's no retention floor; customer policy governs.

AI Identity maps to the operational-evidence subset of each of the
four AI RMF functions. Model-level validity (MS-2.3/MS-2.5 bias +
robustness testing) is the *provider's* responsibility and explicitly
out of scope.

Function → artifact mapping:

| Function | Artifact | Subcategories |
|---|---|---|
| GOVERN | ``govern.json`` | GV-1.1 through GV-6.2 (policies, accountability, roles) |
| MAP | ``map.json`` | MP-4.1 (authorized use), MP-5.1 (impact classification) |
| MEASURE | ``measure_audit_log.csv`` | MS-4.1, MS-4.3 (post-deployment monitoring) |
| MEASURE | ``measure_chain_integrity.json`` | MS-2.5 (validity evidence) |
| MEASURE | ``control_results.csv`` | MS-4.1 |
| MEASURE | ``attestations/*.dsse.json`` | MS-2.5 |
| MANAGE | ``manage_approvals.csv`` | MG-1.3 mitigation + MG-3.1 accountability |
| MANAGE | ``manage_revocations.csv`` | MG-2.4 incident response (identity compromise) |

Known gaps surfaced in ``evidence_summary.known_gaps``:

- Impact assessment records (MP-5.1) — customer-authored PDFs, not
  captured by the runtime governance layer. Potential future feature:
  per-agent impact-assessment uploads.
- Bias / validity testing (MS-2.3, MS-2.5) — model-level validity is
  the provider's responsibility, not the runtime governance layer.
- Anomaly detection (MS-4.1 recommended artifact) — no anomaly system
  shipped yet. Listed as a gap; a future builder will include it.
"""

from __future__ import annotations

import csv
import datetime  # noqa: TC003 — runtime use in _rfc3339
import hashlib
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
    ApprovalRequest,
    AuditLog,
    ComplianceReport,
    ComplianceResult,
    ForensicAttestation,
    OrgMembership,
    Policy,
    User,
)
from common.validation.eu_ai_act import ANNEX_III_CATEGORIES, NOT_IN_SCOPE

# Lifecycle action_types that show up in audit_log.request_metadata
# whenever a key/agent is revoked. Used to populate
# ``manage_revocations.csv`` — MG-2.4 incident-response evidence
# for identity compromise.
_REVOCATION_ACTIONS: frozenset[str] = frozenset({"agent_revoked", "key_revoked", "key_rotated"})


# ── Top-level entrypoint ─────────────────────────────────────────────


def build_nist_ai_rmf_bundle(
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
    """Populate ``bundle`` with the full NIST AI RMF 1.0 evidence set.

    Caller is responsible for sealing the bundle — this function only
    writes content.

    ``agent_ids`` narrows the export to a sampling-plan subset; null
    means whole-org. Every query below honors this filter.
    """
    scope_agent_ids = _resolve_scope(db, org_id=org_id, agent_ids=agent_ids)
    scoped_agents = _fetch_scoped_agents(db, org_id=org_id, scope_agent_ids=scope_agent_ids)

    _write_govern(
        bundle,
        db,
        org_id=org_id,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    _write_map(bundle, scoped_agents)
    access_count = _write_measure_audit_log(
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
    chain_result = _write_measure_chain_integrity(bundle, db, built_at=built_at)
    control_result_count = _write_control_results(
        bundle,
        db,
        org_id=org_id,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    approval_count = _write_manage_approvals(
        bundle,
        db,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    revocation_count = _write_manage_revocations(
        bundle,
        db,
        org_id=org_id,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )

    _write_evidence_summary(
        bundle,
        export_id=export_id,
        org_id=org_id,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
        built_at=built_at,
        agent_ids=agent_ids,
        counts={
            "agents_mapped": len(scoped_agents),
            "access_log": access_count,
            "attestations": attestation_count,
            "control_results": control_result_count,
            "approvals": approval_count,
            "revocations": revocation_count,
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
    if agent_ids is not None:
        return list(agent_ids)
    rows = db.query(Agent.id).filter(Agent.org_id == org_id).order_by(Agent.id.asc()).all()
    return [r[0] for r in rows]


def _fetch_scoped_agents(
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
) -> list[Agent]:
    query = db.query(Agent).filter(Agent.org_id == org_id)
    if scope_agent_ids:
        query = query.filter(Agent.id.in_(scope_agent_ids))
    return query.order_by(Agent.id.asc()).all()


# ── GOVERN ──────────────────────────────────────────────────────────


def _write_govern(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> None:
    """GOVERN evidence — policy catalog, role assignments, bindings.

    Aggregates three views:
    - policy_catalog: every Policy row for agents in scope, with
      rules_sha256 + version + activity state.
    - role_assignments: OrgMembership entries for the org (GV-2.1
      accountability evidence).
    - agent_policy_bindings: which policies are currently attached to
      which agents (GV-1.1 policy application).
    """
    # policy_catalog
    if scope_agent_ids:
        policies = (
            db.query(Policy)
            .filter(
                Policy.agent_id.in_(scope_agent_ids),
                Policy.updated_at >= audit_period_start,
                Policy.updated_at <= audit_period_end,
            )
            .order_by(Policy.agent_id.asc(), Policy.version.asc())
            .all()
        )
    else:
        policies = []
    policy_catalog = [
        {
            "policy_id": p.id,
            "agent_id": str(p.agent_id),
            "version": p.version,
            "is_active": p.is_active,
            "rules_sha256": hashlib.sha256(
                json.dumps(p.rules or {}, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "created_at": _rfc3339(p.created_at),
            "updated_at": _rfc3339(p.updated_at),
        }
        for p in policies
    ]

    # role_assignments (GV-2.1)
    memberships = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == org_id)
        .order_by(OrgMembership.user_id.asc())
        .all()
    )
    role_assignments = [
        {
            "user_id": str(m.user_id),
            "org_id": str(m.org_id),
            "role": m.role,
        }
        for m in memberships
    ]

    # agent_policy_bindings — currently-active policies per agent
    # (GV-1.1 — the actual controls in effect at export time)
    if scope_agent_ids:
        active_bindings = (
            db.query(Policy.agent_id, Policy.id)
            .filter(
                Policy.agent_id.in_(scope_agent_ids),
                Policy.is_active.is_(True),
            )
            .order_by(Policy.agent_id.asc())
            .all()
        )
    else:
        active_bindings = []
    bindings_by_agent: dict[str, list[int]] = {}
    for agent_id, policy_id in active_bindings:
        bindings_by_agent.setdefault(str(agent_id), []).append(policy_id)
    agent_policy_bindings = [
        {"agent_id": aid, "active_policy_ids": sorted(pids)}
        for aid, pids in sorted(bindings_by_agent.items())
    ]

    bundle.write_json(
        "govern.json",
        {
            "function": "GOVERN",
            "subcategories_covered": ["GV-1.1", "GV-2.1", "GV-6.1"],
            "policy_catalog": policy_catalog,
            "role_assignments": role_assignments,
            "agent_policy_bindings": agent_policy_bindings,
            "limitations": [
                "Model-lifecycle governance (training, evaluation, "
                "release cadence) is the provider's responsibility and "
                "not captured by this export.",
            ],
        },
        controls=["NIST-GV-1.1", "NIST-GV-2.1", "NIST-GV-6.1"],
    )


# ── MAP ─────────────────────────────────────────────────────────────


def _write_map(bundle: ComplianceExportBundle, agents: list[Agent]) -> None:
    """MAP evidence — agent inventory + capability + risk classification.

    Satisfies MP-4.1 (authorized use — we show what each agent is
    authorized to do) and MP-5.1 (impact — via the shared
    eu_ai_act_risk_class field, unified across profiles per the
    cross-framework mapping table).
    """
    entries = []
    for a in agents:
        code = a.eu_ai_act_risk_class
        if code is None:
            risk = {"code": "", "description": "", "status": "unclassified"}
        elif code == NOT_IN_SCOPE:
            risk = {
                "code": NOT_IN_SCOPE,
                "description": (
                    "Deployer determined this agent is out of scope for "
                    "Annex III high-risk classification."
                ),
                "status": "out_of_scope",
            }
        else:
            risk = {
                "code": code,
                "description": ANNEX_III_CATEGORIES.get(code, "Unknown"),
                "status": "in_scope",
            }
        entries.append(
            {
                "agent_id": str(a.id),
                "name": a.name,
                "status": a.status,
                "description": a.description or "",
                "capabilities": list(a.capabilities or []),
                "risk_classification": risk,
                "created_at": _rfc3339(a.created_at),
                "updated_at": _rfc3339(a.updated_at),
            }
        )

    bundle.write_json(
        "map.json",
        {
            "function": "MAP",
            "subcategories_covered": ["MP-4.1", "MP-5.1"],
            "agents": entries,
            "limitations": [
                "Impact assessment records (MP-5.1 recommended): "
                "deployment-time impact assessments are typically "
                "authored externally as PDFs and not captured by the "
                "runtime governance layer. Per-agent impact-assessment "
                "uploads are a potential future feature.",
                "Bias / validity testing (MS-2.3, MS-2.5): model-level "
                "validity is the provider's responsibility and not "
                "captured by this export.",
            ],
        },
        controls=["NIST-MP-4.1", "NIST-MP-5.1"],
    )


# ── MEASURE ─────────────────────────────────────────────────────────


def _write_measure_audit_log(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Every audit_log row in scope. MS-4.1 / MS-4.3 post-deployment
    monitoring.
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
        path="measure_audit_log.csv",
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
        controls=["NIST-MS-4.1", "NIST-MS-4.3"],
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
    """Forensic attestations in period. MS-2.5 validity evidence."""
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
            controls=["NIST-MS-2.5"],
        )
    return len(attestations)


def _write_measure_chain_integrity(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    built_at: datetime.datetime,
) -> dict:
    """verify_chain() at export time. MS-2.5."""
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
        "measure_chain_integrity.json",
        payload,
        controls=["NIST-MS-2.5"],
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
    """Automated compliance-check results in the period. MS-4.1."""
    org_user_ids = [u[0] for u in db.query(User.id).filter(User.org_id == org_id).all()]
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
        controls=["NIST-MS-4.1"],
    )
    return len(rows)


# ── MANAGE ──────────────────────────────────────────────────────────


def _write_manage_approvals(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Approval records — MG-1.3 mitigation + MG-3.1 accountability."""
    if not scope_agent_ids:
        _write_csv(
            bundle,
            path="manage_approvals.csv",
            fieldnames=_APPROVAL_COLS,
            rows=[],
            controls=["NIST-MG-1.3", "NIST-MG-3.1"],
        )
        return 0
    query = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.agent_id.in_(scope_agent_ids),
            ApprovalRequest.created_at >= audit_period_start,
            ApprovalRequest.created_at <= audit_period_end,
        )
        .order_by(ApprovalRequest.created_at.asc(), ApprovalRequest.id.asc())
    )
    rows = [
        {
            "request_id": str(req.id),
            "created_at": _rfc3339(req.created_at),
            "agent_id": str(req.agent_id),
            "user_id": str(req.user_id),
            "endpoint": req.endpoint,
            "method": req.method,
            "status": req.status,
            "reviewer_id": str(req.reviewer_id) if req.reviewer_id else "",
            "reviewer_note": req.reviewer_note or "",
            "resolved_at": _rfc3339(req.resolved_at) if req.resolved_at else "",
            "expires_at": _rfc3339(req.expires_at),
        }
        for req in query.all()
    ]
    _write_csv(
        bundle,
        path="manage_approvals.csv",
        fieldnames=_APPROVAL_COLS,
        rows=rows,
        controls=["NIST-MG-1.3", "NIST-MG-3.1"],
    )
    return len(rows)


_APPROVAL_COLS = [
    "request_id",
    "created_at",
    "agent_id",
    "user_id",
    "endpoint",
    "method",
    "status",
    "reviewer_id",
    "reviewer_note",
    "resolved_at",
    "expires_at",
]


def _write_manage_revocations(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    org_id: uuid.UUID,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Revocation events — MG-2.4 incident response for identity compromise.

    Combines two sources into one CSV with a ``revocation_type`` column:

    1. Agent revocations — rows from ``agents`` where
       ``revoked_at`` falls in the period. Direct, authoritative.
    2. Key revocations — reconstructed from ``audit_log`` rows whose
       ``request_metadata.action_type`` is in the revocation set. We
       pull from audit_log rather than ``agent_keys`` directly because
       the keys table has no ``revoked_at`` timestamp; the audit row is
       the source of truth for *when* a rotation/revocation happened.
    """
    rows: list[dict] = []

    # Agent revocations — direct from Agent model.
    agent_query = db.query(Agent).filter(
        Agent.org_id == org_id,
        Agent.revoked_at.isnot(None),
        Agent.revoked_at >= audit_period_start,
        Agent.revoked_at <= audit_period_end,
    )
    if scope_agent_ids:
        agent_query = agent_query.filter(Agent.id.in_(scope_agent_ids))
    for agent in agent_query.order_by(Agent.revoked_at.asc(), Agent.id.asc()).all():
        rows.append(
            {
                "event_at": _rfc3339(agent.revoked_at),
                "revocation_type": "agent",
                "subject_id": str(agent.id),
                "subject_name": agent.name,
                "actor_user_id": "",
                "source": "agents.revoked_at",
                "details_json": json.dumps({"status": agent.status}, sort_keys=True),
            }
        )

    # Key revocations + rotations — from audit_log.
    audit_query = (
        db.query(AuditLog)
        .filter(
            AuditLog.org_id == org_id,
            AuditLog.created_at >= audit_period_start,
            AuditLog.created_at <= audit_period_end,
        )
        .order_by(AuditLog.id.asc())
    )
    if scope_agent_ids:
        audit_query = audit_query.filter(AuditLog.agent_id.in_(scope_agent_ids))
    for entry in audit_query.all():
        metadata = entry.request_metadata or {}
        action = metadata.get("action_type")
        if action not in _REVOCATION_ACTIONS:
            continue
        rows.append(
            {
                "event_at": _rfc3339(entry.created_at),
                "revocation_type": action.replace("_revoked", "").replace("_rotated", "")
                if action != "agent_revoked"
                else "agent",
                "subject_id": str(entry.agent_id) if entry.agent_id else "",
                "subject_name": entry.agent_name or metadata.get("agent_name", "") or "",
                "actor_user_id": str(entry.user_id) if entry.user_id else "",
                "source": "audit_log",
                "details_json": json.dumps(
                    {k: v for k, v in metadata.items() if k not in {"action_type"}},
                    sort_keys=True,
                ),
            }
        )

    # Sort the combined list so ordering is deterministic across runs.
    rows.sort(key=lambda r: (r["event_at"], r["revocation_type"], r["subject_id"]))

    _write_csv(
        bundle,
        path="manage_revocations.csv",
        fieldnames=[
            "event_at",
            "revocation_type",
            "subject_id",
            "subject_name",
            "actor_user_id",
            "source",
            "details_json",
        ],
        rows=rows,
        controls=["NIST-MG-2.4"],
    )
    return len(rows)


# ── Evidence summary ────────────────────────────────────────────────


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
    """Auditor index: function → artifact mapping + counts + gaps."""
    bundle.write_json(
        "evidence_summary.json",
        {
            "profile": "nist_ai_rmf_1_0",
            "framework_nature": "voluntary",
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
            "function_artifact_mapping": {
                "GOVERN": ["govern.json"],
                "MAP": ["map.json"],
                "MEASURE": [
                    "measure_audit_log.csv",
                    "measure_chain_integrity.json",
                    "attestations/*.dsse.json",
                    "control_results.csv",
                ],
                "MANAGE": ["manage_approvals.csv", "manage_revocations.csv"],
            },
            "artifact_control_mapping": {
                "govern.json": ["NIST-GV-1.1", "NIST-GV-2.1", "NIST-GV-6.1"],
                "map.json": ["NIST-MP-4.1", "NIST-MP-5.1"],
                "measure_audit_log.csv": ["NIST-MS-4.1", "NIST-MS-4.3"],
                "measure_chain_integrity.json": ["NIST-MS-2.5"],
                "attestations/*.dsse.json": ["NIST-MS-2.5"],
                "control_results.csv": ["NIST-MS-4.1"],
                "manage_approvals.csv": ["NIST-MG-1.3", "NIST-MG-3.1"],
                "manage_revocations.csv": ["NIST-MG-2.4"],
            },
            "known_gaps": [
                "MP-5.1 impact assessments: customer-authored PDFs are "
                "not captured by the runtime layer. Per-agent impact "
                "uploads are a potential future feature.",
                "MS-2.3 / MS-2.5 bias + validity testing: model-level "
                "validity is the provider's responsibility.",
                "MS-4.1 anomaly detection: no anomaly-detection system "
                "shipped yet; a future builder will include it.",
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
    """Serialize rows to RFC 4180 CSV and add to the bundle."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    bundle.write_text(path, buf.getvalue(), controls=controls)


def _rfc3339(value: datetime.datetime) -> str:
    """ISO 8601 / RFC 3339 with explicit UTC ``Z`` suffix."""
    if value.tzinfo is None:
        utc = value.replace(tzinfo=datetime.UTC)
    else:
        utc = value.astimezone(datetime.UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["build_nist_ai_rmf_bundle"]
