"""Compliance evaluation engine — runs automated checks against the database.

Each check_query maps to a function that inspects agents, policies, keys,
credentials, and audit logs to determine pass/fail/warning status.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from common.audit.writer import verify_chain
from common.models import (
    Agent,
    AgentKey,
    AuditLog,
    ComplianceCheck,
    ComplianceReport,
    ComplianceResult,
    Policy,
    UpstreamCredential,
)

logger = logging.getLogger("ai_identity.compliance")


def evaluate_check(
    check: ComplianceCheck,
    db: Session,
    user_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
) -> dict:
    """Evaluate a single compliance check.

    Returns: {"status": "pass|fail|warning|not_applicable", "evidence": {...}, "remediation": "..."}
    """
    query_fn = CHECK_REGISTRY.get(check.check_query)
    if not query_fn:
        return {
            "status": "not_applicable",
            "evidence": {"reason": f"No evaluator for check_query={check.check_query}"},
            "remediation": None,
        }

    try:
        return query_fn(db, user_id, agent_id)
    except Exception as e:
        logger.error("Check %s failed: %s", check.code, e)
        return {
            "status": "warning",
            "evidence": {"error": str(e)},
            "remediation": "Check evaluation encountered an error — review manually.",
        }


def run_assessment(
    db: Session,
    report: ComplianceReport,
    checks: list[ComplianceCheck],
    user_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
) -> None:
    """Run all checks for a report and update results + score."""
    passed = 0
    failed = 0
    total_applicable = 0

    for check in checks:
        result_data = evaluate_check(check, db, user_id, agent_id)

        result = ComplianceResult(
            report_id=report.id,
            check_id=check.id,
            status=result_data["status"],
            evidence=result_data.get("evidence"),
            remediation=result_data.get("remediation"),
        )
        db.add(result)

        if result_data["status"] in ("pass", "fail", "warning"):
            total_applicable += 1
        if result_data["status"] == "pass":
            passed += 1
        if result_data["status"] == "fail":
            failed += 1

    # Calculate score
    score = round((passed / total_applicable) * 100, 1) if total_applicable > 0 else None

    # Generate summary
    if score is not None:
        if score >= 90:
            summary = (
                f"Strong compliance posture: {passed}/{total_applicable} checks passed ({score}%)"
            )
        elif score >= 70:
            summary = f"Moderate compliance: {passed}/{total_applicable} passed, {failed} failed ({score}%)"
        else:
            summary = f"Compliance gaps detected: {failed} failures out of {total_applicable} checks ({score}%)"
    else:
        summary = "No applicable checks evaluated."

    report.score = score
    report.summary = summary
    report.status = "completed"
    db.commit()


# ── Check Implementations ────────────────────────────────────────────


def _check_all_agents_have_policies(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """Every active agent should have at least one active policy."""

    query = db.query(Agent).filter(Agent.user_id == user_id, Agent.status == "active")
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    agents = query.all()
    if not agents:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active agents found"},
            "remediation": None,
        }

    # Single query: get agent_ids that have at least one active policy
    agent_ids = [a.id for a in agents]
    agents_with_policies = set(
        row[0]
        for row in db.query(Policy.agent_id)
        .filter(Policy.agent_id.in_(agent_ids), Policy.is_active.is_(True))
        .group_by(Policy.agent_id)
        .all()
    )

    missing = [
        {"agent_id": str(a.id), "name": a.name} for a in agents if a.id not in agents_with_policies
    ]

    if missing:
        return {
            "status": "fail",
            "evidence": {"agents_without_policies": missing, "total_agents": len(agents)},
            "remediation": "Create an active policy for each agent via POST /api/v1/agents/{id}/policies",
        }
    return {
        "status": "pass",
        "evidence": {"total_agents": len(agents), "all_have_policies": True},
        "remediation": None,
    }


def _check_no_wildcard_only_policies(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """Policies should not use '*' as the only allowed endpoint."""
    query = (
        db.query(Policy, Agent)
        .join(Agent)
        .filter(Agent.user_id == user_id, Policy.is_active.is_(True))
    )
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    overly_permissive = []
    for policy, agent in query.all():
        rules = policy.rules or {}
        endpoints = rules.get("allowed_endpoints", [])
        if endpoints == ["*"] and not rules.get("denied_endpoints"):
            overly_permissive.append(
                {
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "policy_id": policy.id,
                }
            )

    if overly_permissive:
        return {
            "status": "fail",
            "evidence": {"wildcard_policies": overly_permissive},
            "remediation": "Replace wildcard '*' with specific endpoint patterns (e.g., '/v1/chat', '/v1/embeddings')",
        }
    return {
        "status": "pass",
        "evidence": {"all_policies_scoped": True},
        "remediation": None,
    }


def _check_audit_chain_integrity(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """The HMAC audit chain should be intact."""
    try:
        result = verify_chain(db, agent_id=agent_id)
        if result["valid"]:
            return {
                "status": "pass",
                "evidence": {
                    "entries_verified": result["entries_verified"],
                    "chain_intact": True,
                },
                "remediation": None,
            }
        else:
            return {
                "status": "fail",
                "evidence": {
                    "first_broken_id": result.get("first_broken_id"),
                    "message": result.get("message"),
                },
                "remediation": "Investigate broken audit chain — possible tampering or data corruption.",
            }
    except Exception as e:
        # No audit entries is not a failure, just not applicable
        if "no entries" in str(e).lower() or "empty" in str(e).lower():
            return {
                "status": "warning",
                "evidence": {"reason": "No audit entries found"},
                "remediation": "Generate traffic through the gateway to create audit entries.",
            }
        raise


def _check_credentials_encrypted(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """All stored credentials should be encrypted at rest."""
    query = (
        db.query(UpstreamCredential, Agent)
        .join(Agent)
        .filter(Agent.user_id == user_id, UpstreamCredential.status == "active")
    )
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    creds = query.all()
    if not creds:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active credentials stored"},
            "remediation": None,
        }

    unencrypted = []
    for cred, agent in creds:
        if not cred.encrypted_key or len(cred.encrypted_key) < 20:
            unencrypted.append(
                {
                    "credential_id": cred.id,
                    "agent_name": agent.name,
                    "provider": cred.provider,
                }
            )

    if unencrypted:
        return {
            "status": "fail",
            "evidence": {"unencrypted_credentials": unencrypted},
            "remediation": "Re-store credentials via the API — encryption is applied automatically.",
        }
    return {
        "status": "pass",
        "evidence": {"total_credentials": len(creds), "all_encrypted": True},
        "remediation": None,
    }


def _check_key_rotation_within_90_days(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """Active keys should have been created or rotated within the last 90 days."""
    cutoff = datetime.now(UTC) - timedelta(days=90)

    query = (
        db.query(AgentKey, Agent)
        .join(Agent)
        .filter(
            Agent.user_id == user_id,
            AgentKey.status == "active",
        )
    )
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    stale_keys = []
    total = 0
    for key, agent in query.all():
        total += 1
        if key.created_at < cutoff:
            stale_keys.append(
                {
                    "key_id": key.id,
                    "key_prefix": key.key_prefix,
                    "agent_name": agent.name,
                    "created_at": key.created_at.isoformat(),
                    "age_days": (datetime.now(UTC) - key.created_at).days,
                }
            )

    if not total:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active keys found"},
            "remediation": None,
        }

    if stale_keys:
        return {
            "status": "warning" if len(stale_keys) < total else "fail",
            "evidence": {"stale_keys": stale_keys, "total_active_keys": total},
            "remediation": "Rotate keys via POST /api/v1/agents/{id}/keys/rotate",
        }
    return {
        "status": "pass",
        "evidence": {"total_active_keys": total, "all_within_90_days": True},
        "remediation": None,
    }


def _check_key_type_separation(db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None) -> dict:
    """Agents should not have both runtime and admin keys active simultaneously."""

    query = db.query(Agent).filter(Agent.user_id == user_id, Agent.status == "active")
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    agents = query.all()
    agent_ids = [a.id for a in agents]

    if not agent_ids:
        return {
            "status": "pass",
            "evidence": {"key_separation_clean": True},
            "remediation": None,
        }

    # Single query: get distinct key_types per agent
    key_type_rows = (
        db.query(AgentKey.agent_id, AgentKey.key_type)
        .filter(AgentKey.agent_id.in_(agent_ids), AgentKey.status == "active")
        .distinct()
        .all()
    )

    # Group key types by agent
    agent_key_types: dict[uuid.UUID, set[str]] = {}
    for aid, kt in key_type_rows:
        agent_key_types.setdefault(aid, set()).add(kt)

    agent_map = {a.id: a for a in agents}
    violations = [
        {
            "agent_id": str(aid),
            "agent_name": agent_map[aid].name,
            "active_key_types": list(types),
        }
        for aid, types in agent_key_types.items()
        if "runtime" in types and "admin" in types
    ]

    if violations:
        return {
            "status": "warning",
            "evidence": {"agents_with_mixed_keys": violations},
            "remediation": "Consider separating admin and runtime key usage across different agents.",
        }
    return {
        "status": "pass",
        "evidence": {"key_separation_clean": True},
        "remediation": None,
    }


def _check_no_revoked_agents_with_active_keys(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """Revoked agents should not have any active keys."""
    from sqlalchemy import func as sqla_func

    query = db.query(Agent).filter(Agent.user_id == user_id, Agent.status == "revoked")
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    agents = query.all()
    agent_ids = [a.id for a in agents]

    if not agent_ids:
        return {
            "status": "pass",
            "evidence": {"no_orphaned_keys": True},
            "remediation": None,
        }

    # Single query: count active keys per revoked agent
    key_counts = dict(
        db.query(AgentKey.agent_id, sqla_func.count(AgentKey.id))
        .filter(AgentKey.agent_id.in_(agent_ids), AgentKey.status == "active")
        .group_by(AgentKey.agent_id)
        .all()
    )

    agent_map = {a.id: a for a in agents}
    violations = [
        {
            "agent_id": str(aid),
            "agent_name": agent_map[aid].name,
            "active_keys": count,
        }
        for aid, count in key_counts.items()
        if count > 0
    ]

    if violations:
        return {
            "status": "fail",
            "evidence": {"revoked_agents_with_active_keys": violations},
            "remediation": "Revoke all keys for revoked agents via DELETE /api/v1/agents/{id}/keys/{key_id}",
        }
    return {
        "status": "pass",
        "evidence": {"no_orphaned_keys": True},
        "remediation": None,
    }


def _check_audit_entries_exist(db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None) -> dict:
    """There should be audit log entries for active agents."""
    query = db.query(Agent).filter(Agent.user_id == user_id, Agent.status == "active")
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    agents = query.all()
    if not agents:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active agents"},
            "remediation": None,
        }

    agent_ids = [a.id for a in agents]

    # Single query: get agent_ids that have at least one audit entry
    agents_with_audit = set(
        row[0]
        for row in db.query(AuditLog.agent_id)
        .filter(AuditLog.agent_id.in_(agent_ids))
        .distinct()
        .all()
    )

    agents_without_audit = [
        {"agent_id": str(a.id), "agent_name": a.name}
        for a in agents
        if a.id not in agents_with_audit
    ]

    if agents_without_audit:
        return {
            "status": "warning",
            "evidence": {"agents_without_audit": agents_without_audit, "total_agents": len(agents)},
            "remediation": "Route traffic through the gateway to generate audit trail entries.",
        }
    return {
        "status": "pass",
        "evidence": {"total_agents": len(agents), "all_have_audit_entries": True},
        "remediation": None,
    }


def _check_credentials_have_prefixes(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """All credentials should have key_prefix set for identification."""
    query = (
        db.query(UpstreamCredential, Agent)
        .join(Agent)
        .filter(Agent.user_id == user_id, UpstreamCredential.status == "active")
    )
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    missing_prefix = []
    total = 0
    for cred, agent in query.all():
        total += 1
        if not cred.key_prefix:
            missing_prefix.append(
                {
                    "credential_id": cred.id,
                    "agent_name": agent.name,
                    "provider": cred.provider,
                }
            )

    if not total:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active credentials"},
            "remediation": None,
        }

    if missing_prefix:
        return {
            "status": "warning",
            "evidence": {"missing_prefix": missing_prefix},
            "remediation": "Re-store credentials — prefix is generated automatically from the key.",
        }
    return {
        "status": "pass",
        "evidence": {"total_credentials": total, "all_have_prefixes": True},
        "remediation": None,
    }


def _check_agent_has_description(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """Active agents should have descriptions for transparency."""
    query = db.query(Agent).filter(Agent.user_id == user_id, Agent.status == "active")
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    missing = []
    total = 0
    for agent in query.all():
        total += 1
        if not agent.description:
            missing.append({"agent_id": str(agent.id), "name": agent.name})

    if not total:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active agents"},
            "remediation": None,
        }

    if missing:
        return {
            "status": "warning",
            "evidence": {"agents_without_description": missing, "total": total},
            "remediation": "Add descriptions via PUT /api/v1/agents/{id} for AI Act transparency compliance.",
        }
    return {
        "status": "pass",
        "evidence": {"total_agents": total, "all_have_descriptions": True},
        "remediation": None,
    }


def _check_agent_capabilities_defined(
    db: Session, user_id: uuid.UUID, agent_id: uuid.UUID | None
) -> dict:
    """Agents should have capabilities explicitly declared."""
    query = db.query(Agent).filter(Agent.user_id == user_id, Agent.status == "active")
    if agent_id:
        query = query.filter(Agent.id == agent_id)

    missing = []
    total = 0
    for agent in query.all():
        total += 1
        if not agent.capabilities:
            missing.append({"agent_id": str(agent.id), "name": agent.name})

    if not total:
        return {
            "status": "not_applicable",
            "evidence": {"reason": "No active agents"},
            "remediation": None,
        }

    if missing:
        return {
            "status": "warning",
            "evidence": {"agents_without_capabilities": missing, "total": total},
            "remediation": "Define capabilities via PUT /api/v1/agents/{id} with a list of capability strings.",
        }
    return {
        "status": "pass",
        "evidence": {"total_agents": total, "all_have_capabilities": True},
        "remediation": None,
    }


# ── Check Registry ───────────────────────────────────────────────────
# Maps check_query values to evaluation functions

CHECK_REGISTRY: dict = {
    "all_agents_have_policies": _check_all_agents_have_policies,
    "no_wildcard_only_policies": _check_no_wildcard_only_policies,
    "audit_chain_integrity": _check_audit_chain_integrity,
    "credentials_encrypted": _check_credentials_encrypted,
    "key_rotation_90_days": _check_key_rotation_within_90_days,
    "key_type_separation": _check_key_type_separation,
    "no_revoked_agents_active_keys": _check_no_revoked_agents_with_active_keys,
    "audit_entries_exist": _check_audit_entries_exist,
    "credentials_have_prefixes": _check_credentials_have_prefixes,
    "agent_has_description": _check_agent_has_description,
    "agent_capabilities_defined": _check_agent_capabilities_defined,
}
