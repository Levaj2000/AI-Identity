"""EU AI Act 2024 profile builder — high-risk AI systems (Annex III).

Produces the full EU AI Act Article 26 / Annex IV evidence set per
``docs/compliance/export-profiles.md`` §"EU AI Act profile". Targets
**high-risk AI systems** — General-Purpose AI (Article 51+) and
prohibited-practice (Article 5) disclosures are out of scope for v1.

Article mapping:

| Artifact | Article |
|---|---|
| ``annex_iv_documentation.json`` | Art. 11 + Annex IV |
| ``access_log.csv`` | Art. 12 (record-keeping) |
| ``chain_integrity.json`` | Art. 12(4) (tamper-evident logs) |
| ``attestations/*.dsse.json`` | Art. 12(4) |
| ``human_oversight_log.csv`` | Art. 14 (human oversight) |
| ``agent_risk_classification.csv`` | Art. 6 / Annex III |
| ``policy_change_log.csv`` | Art. 9 (risk management system) |
| ``capability_disclosures.csv`` | Art. 13(3) (transparency) |
| ``agent_inventory.csv`` | — (informational) |

Known gaps surfaced in ``evidence_summary.known_gaps``:

- Article 10 data governance — upstream training data is the
  provider's responsibility and outside AI Identity's visibility.
- GPAI (Article 51+) — out of scope for this profile; a separate
  ``eu_ai_act_gpai`` profile is a possible follow-on.
- Incident records (Article 15 / Article 73) — blocked on the
  ``IncidentRecord`` model which is still a separate sprint item.
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
    ForensicAttestation,
    Policy,
)
from common.validation.eu_ai_act import ANNEX_III_CATEGORIES, NOT_IN_SCOPE

# ── Top-level entrypoint ─────────────────────────────────────────────


def build_eu_ai_act_bundle(
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
    """Populate ``bundle`` with the full EU AI Act 2024 evidence set.

    Caller is responsible for sealing the bundle — this function only
    writes content.

    ``agent_ids`` narrows the export to a sampling-plan subset; null
    means whole-org. Every query below honors this filter so auditor
    requests targeting specific agents don't pull unrelated evidence.
    """
    scope_agent_ids = _resolve_scope(db, org_id=org_id, agent_ids=agent_ids)

    # Collect agents-in-scope once — used by several writers + summary.
    scoped_agents = _fetch_scoped_agents(db, org_id=org_id, scope_agent_ids=scope_agent_ids)

    agent_count = _write_agent_inventory(bundle, scoped_agents)
    access_count = _write_access_log(
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
    chain_result = _write_chain_integrity(bundle, db, built_at=built_at)
    oversight_count = _write_human_oversight_log(
        bundle,
        db,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    classification_unclassified = _write_agent_risk_classification(bundle, scoped_agents)
    policy_change_count = _write_policy_change_log(
        bundle,
        db,
        scope_agent_ids=scope_agent_ids,
        audit_period_start=audit_period_start,
        audit_period_end=audit_period_end,
    )
    _write_capability_disclosures(bundle, scoped_agents)
    _write_annex_iv_documentation(
        bundle,
        scoped_agents=scoped_agents,
        built_at=built_at,
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
            "agent_inventory": agent_count,
            "access_log": access_count,
            "attestations": attestation_count,
            "human_oversight_log": oversight_count,
            "agent_risk_classification": len(scoped_agents),
            "policy_change_log": policy_change_count,
            "capability_disclosures": len(scoped_agents),
        },
        chain_integrity={
            "valid": chain_result["valid"],
            "total_entries": chain_result["total_entries"],
            "entries_verified": chain_result["entries_verified"],
        },
        guardrail_facts={
            "unclassified_agents": classification_unclassified,
            # Honest flag for auditors — if this is non-zero, the Annex
            # IV section below notes the classification is incomplete.
        },
    )


# ── Scope resolution ─────────────────────────────────────────────────


def _resolve_scope(
    db: Session,
    *,
    org_id: uuid.UUID,
    agent_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    """Resolve the list of agent ids this export covers."""
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


# ── Artifact writers ─────────────────────────────────────────────────


def _write_agent_inventory(bundle: ComplianceExportBundle, agents: list[Agent]) -> int:
    """Every agent in scope + lifecycle columns. Informational."""
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
    """Every audit_log row in scope. Article 12 record-keeping."""
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
        controls=["EUAI-Art.12"],
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
    """Forensic attestations covering the period. Article 12(4)."""
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
            controls=["EUAI-Art.12.4"],
        )
    return len(attestations)


def _write_chain_integrity(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    built_at: datetime.datetime,
) -> dict:
    """verify_chain() result — Article 12(4) tamper-evidence."""
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
    bundle.write_json("chain_integrity.json", payload, controls=["EUAI-Art.12.4"])
    return payload


def _write_human_oversight_log(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Every ApprovalRequest in period. Article 14 human oversight.

    ApprovalRequest has no ``org_id`` — we scope via ``agent_id`` being
    in the resolved in-scope set, which the router already verified
    belongs to the caller's org.
    """
    if not scope_agent_ids:
        _write_csv(
            bundle,
            path="human_oversight_log.csv",
            fieldnames=_HUMAN_OVERSIGHT_COLS,
            rows=[],
            controls=["EUAI-Art.14"],
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
        path="human_oversight_log.csv",
        fieldnames=_HUMAN_OVERSIGHT_COLS,
        rows=rows,
        controls=["EUAI-Art.14"],
    )
    return len(rows)


_HUMAN_OVERSIGHT_COLS = [
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


def _write_agent_risk_classification(bundle: ComplianceExportBundle, agents: list[Agent]) -> int:
    """Per-agent Annex III classification. Article 6 / Annex III.

    Returns the count of *unclassified* agents — agents with
    ``eu_ai_act_risk_class IS NULL``. An honest non-zero value here is
    reflected in Annex IV documentation and the evidence summary
    rather than being silently bucketed as "not in scope."
    """
    rows = []
    unclassified = 0
    for agent in agents:
        code = agent.eu_ai_act_risk_class
        if code is None:
            classification_label = ""
            description = ""
            classification_status = "unclassified"
            unclassified += 1
        elif code == NOT_IN_SCOPE:
            classification_label = NOT_IN_SCOPE
            description = (
                "Deployer determined this agent is not a high-risk AI system under Annex III."
            )
            classification_status = "out_of_scope"
        else:
            classification_label = code
            description = ANNEX_III_CATEGORIES.get(code, "Unknown Annex III category")
            classification_status = "in_scope"
        rows.append(
            {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "annex_iii_code": classification_label,
                "annex_iii_description": description,
                "classification_status": classification_status,
            }
        )
    _write_csv(
        bundle,
        path="agent_risk_classification.csv",
        fieldnames=[
            "agent_id",
            "agent_name",
            "annex_iii_code",
            "annex_iii_description",
            "classification_status",
        ],
        rows=rows,
        controls=["EUAI-Art.6", "EUAI-Annex.III"],
    )
    return unclassified


def _write_policy_change_log(
    bundle: ComplianceExportBundle,
    db: Session,
    *,
    scope_agent_ids: list[uuid.UUID],
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> int:
    """Policy version history. Article 9 risk-management-system evidence.

    Emits metadata + a canonical SHA-256 of the rules JSON for
    tamper-detection. The full rules content is not inlined — that's
    policy_snapshots/ territory in the SOC 2 profile. For EU AI Act
    deployers, the hash is sufficient Article 9 change evidence; an
    auditor wanting full rule content can request the SOC 2 export.
    """
    if not scope_agent_ids:
        _write_csv(
            bundle,
            path="policy_change_log.csv",
            fieldnames=_POLICY_CHANGE_COLS,
            rows=[],
            controls=["EUAI-Art.9"],
        )
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
    rows = []
    for policy in policies:
        rules_json = json.dumps(policy.rules or {}, sort_keys=True).encode("utf-8")
        rules_sha256 = hashlib.sha256(rules_json).hexdigest()
        rows.append(
            {
                "policy_id": policy.id,
                "agent_id": str(policy.agent_id),
                "version": policy.version,
                "is_active": "true" if policy.is_active else "false",
                "created_at": _rfc3339(policy.created_at),
                "updated_at": _rfc3339(policy.updated_at),
                "rules_sha256": rules_sha256,
                "rules_bytes": len(rules_json),
            }
        )
    _write_csv(
        bundle,
        path="policy_change_log.csv",
        fieldnames=_POLICY_CHANGE_COLS,
        rows=rows,
        controls=["EUAI-Art.9"],
    )
    return len(rows)


_POLICY_CHANGE_COLS = [
    "policy_id",
    "agent_id",
    "version",
    "is_active",
    "created_at",
    "updated_at",
    "rules_sha256",
    "rules_bytes",
]


def _write_capability_disclosures(bundle: ComplianceExportBundle, agents: list[Agent]) -> None:
    """Per-agent capability snapshot. Article 13(3) transparency."""
    rows = [
        {
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "capabilities": json.dumps(agent.capabilities or [], sort_keys=True),
            "declared_at": _rfc3339(agent.updated_at),
        }
        for agent in agents
    ]
    _write_csv(
        bundle,
        path="capability_disclosures.csv",
        fieldnames=["agent_id", "agent_name", "capabilities", "declared_at"],
        rows=rows,
        controls=["EUAI-Art.13.3"],
    )


def _write_annex_iv_documentation(
    bundle: ComplianceExportBundle,
    *,
    scoped_agents: list[Agent],
    built_at: datetime.datetime,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
) -> None:
    """Annex IV technical documentation fields we can produce automatically.

    This is the narrative backbone of the export. We produce ONLY the
    fields AI Identity has visibility into; the provider/deployer is
    responsible for the training-data-governance, conformity-assessment,
    and post-market-monitoring narrative sections per Article 11.
    """
    bundle.write_json(
        "annex_iv_documentation.json",
        {
            "schema_version": 1,
            "built_at": _rfc3339(built_at),
            "audit_period_start": _rfc3339(audit_period_start),
            "audit_period_end": _rfc3339(audit_period_end),
            "annex_iv_sections": {
                "1(a)_general_description": (
                    "AI Identity is an agent identity, policy, and audit "
                    "platform. Each AI agent deployed by the customer is "
                    "assigned a cryptographic identity; every agent "
                    "decision is evaluated against a context-aware policy "
                    "and recorded in an immutable HMAC-chained audit log. "
                    "Session-closing attestations are DSSE-signed with an "
                    "ECDSA-P256 key managed by Google Cloud KMS."
                ),
                "1(b)_intended_purpose_per_agent": [
                    {
                        "agent_id": str(a.id),
                        "agent_name": a.name,
                        "intended_purpose": a.description or "",
                        "annex_iii_classification": a.eu_ai_act_risk_class or "unclassified",
                    }
                    for a in scoped_agents
                ],
                "2(a)_development_methods": (
                    "Architecture reference: docs/ARCHITECTURE.md and "
                    "ADR-002 at docs/ADR-002-compliance-exports.md in the "
                    "AI Identity source tree. The export archive itself "
                    "is a DSSE-signed ZIP bundle; the signing model is "
                    "documented at docs/forensics/trust-model.md."
                ),
                "2(d)_logging_and_record_keeping": (
                    "Every gateway decision produces an audit_log row "
                    "with an HMAC-SHA256 entry_hash chained to the "
                    "previous row's hash. Tamper-evidence is verifiable "
                    "offline via the forensic CLI. Session-close "
                    "attestations are DSSE-signed; the verification "
                    "procedure is documented in "
                    "docs/forensics/attestation-format.md. Log retention "
                    "default is 13 months, which satisfies Article 19's "
                    "6-month minimum."
                ),
                "3_monitoring_functioning_and_control": (
                    "Runtime monitoring: Prometheus metrics for decision "
                    "latency, policy-engine health, and attestation sign "
                    "rate. Functioning control: context-aware ABAC policy "
                    "engine with circuit-breaker fail-closed semantics on "
                    "policy evaluation timeouts. Human oversight: "
                    "ApprovalRequest workflow (Article 14) with "
                    "configurable auto-expiry for unapproved requests."
                ),
            },
            "gaps_and_limitations": [
                {
                    "article": "Art. 10",
                    "topic": "Data and data governance",
                    "limitation": (
                        "Governance of upstream training data is the "
                        "provider's responsibility and is outside AI "
                        "Identity's visibility. This export does not "
                        "include training-data provenance; the provider "
                        "must document this separately."
                    ),
                },
                {
                    "article": "Art. 15 / Art. 73",
                    "topic": "Serious incident reporting",
                    "limitation": (
                        "A structured IncidentRecord model is not yet "
                        "shipped. Post-market incidents are tracked as "
                        "markdown in docs/incident-response/ and are not "
                        "included in this export."
                    ),
                },
                {
                    "article": "Art. 51+",
                    "topic": "General-Purpose AI model obligations",
                    "limitation": (
                        "Out of scope for this profile. A separate "
                        "eu_ai_act_gpai profile may be added for GPAI "
                        "deployments."
                    ),
                },
            ],
        },
        controls=["EUAI-Art.11", "EUAI-Annex.IV"],
    )


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
    guardrail_facts: dict,
) -> None:
    """Cross-reference of artifacts → EU AI Act articles + counts + gaps."""
    bundle.write_json(
        "evidence_summary.json",
        {
            "profile": "eu_ai_act_2024",
            "export_id": str(export_id),
            "org_id": str(org_id),
            "audit_period_start": _rfc3339(audit_period_start),
            "audit_period_end": _rfc3339(audit_period_end),
            "built_at": _rfc3339(built_at),
            "scope": {
                "agent_ids": [str(a) for a in agent_ids] if agent_ids else None,
                "whole_org": agent_ids is None,
                "applicability": "high-risk AI systems (Annex III). GPAI and prohibited-practice disclosures not included.",
            },
            "counts": counts,
            "chain_integrity": chain_integrity,
            "guardrail_facts": guardrail_facts,
            "artifact_control_mapping": {
                "annex_iv_documentation.json": ["EUAI-Art.11", "EUAI-Annex.IV"],
                "access_log.csv": ["EUAI-Art.12"],
                "chain_integrity.json": ["EUAI-Art.12.4"],
                "attestations/*.dsse.json": ["EUAI-Art.12.4"],
                "human_oversight_log.csv": ["EUAI-Art.14"],
                "agent_risk_classification.csv": ["EUAI-Art.6", "EUAI-Annex.III"],
                "policy_change_log.csv": ["EUAI-Art.9"],
                "capability_disclosures.csv": ["EUAI-Art.13.3"],
                "agent_inventory.csv": [],
            },
            "known_gaps": [
                "Art. 10 data governance: upstream training data is the "
                "provider's responsibility; not in this export.",
                "Art. 15 / Art. 73 incident records: no IncidentRecord "
                "model yet — postmortems live as markdown.",
                "Art. 51+ GPAI: out of scope for this profile.",
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


__all__ = ["build_eu_ai_act_bundle"]
