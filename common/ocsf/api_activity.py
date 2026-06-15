"""Map a gateway ``audit_log`` row to an OCSF **API Activity** event.

Grounded in AI Identity's OCSF contributions, not a hypothetical:
- **class_uid 6003 (API Activity)** with the **``ai_operation`` profile** — the
  shape a gateway/proxy can honestly populate (PR #1641: ``ai_agent`` placement).
- The **``attestation``** object carries the tamper-evident hash-chain linkage
  (``entry_hash`` → next row's ``prev_entry_hash``), the integrity seam from
  PR #1661 — so a consumer can verify provenance offline.
- Producer facts with no native OCSF home (policy version, latency, cost,
  org-chain sequence) go in ``unmapped`` — honest, per the OCSF guidance.

One audit_log row → one OCSF event. See docs/ocsf-pr1641-consumer-example.md
and docs/cosai-ws4-ocsf-mapping/CMF-OCSF-CROSSMAP.md for the source mapping.
"""

from __future__ import annotations

from typing import Any

OCSF_VERSION = "1.9.0-dev"

# OCSF API Activity ``activity_id``: 1 Create, 2 Read, 3 Update, 4 Delete, 0 Unknown.
_METHOD_ACTIVITY: dict[str, int] = {
    "POST": 1,
    "GET": 2,
    "HEAD": 2,
    "PUT": 3,
    "PATCH": 3,
    "DELETE": 4,
}

# OCSF base ``action_id``: 1 Allowed, 2 Denied, 99 Other, 0 Unknown.
_DECISION_ACTION: dict[str, tuple[int, str]] = {
    "allow": (1, "Allowed"),
    "deny": (2, "Denied"),
    "error": (99, "Other"),
}


def audit_log_to_ocsf(row: Any) -> dict[str, Any]:
    """Transform an ``AuditLog`` ORM row into a single OCSF API Activity event."""
    method = (row.method or "").upper()
    decision = (row.decision or "").lower()
    activity_id = _METHOD_ACTIVITY.get(method, 0)
    action_id, action = _DECISION_ACTION.get(decision, (0, "Unknown"))

    # OCSF ``time`` is epoch milliseconds.
    time_ms = int(row.created_at.timestamp() * 1000) if row.created_at else None

    # severity_id: 1 Informational (allow) · 3 Medium (deny/error) — a denied or
    # errored agent action is more interesting to a SOC than an allowed one.
    severity_id = 1 if decision == "allow" else 3

    metadata: dict[str, Any] = {"version": OCSF_VERSION, "profiles": ["ai_operation"]}
    if row.correlation_id:
        metadata["correlation_uid"] = row.correlation_id

    event: dict[str, Any] = {
        "activity_id": activity_id,
        "category_uid": 6,  # Application Activity
        "class_uid": 6003,  # API Activity
        "type_uid": 6003 * 100 + activity_id,
        "severity_id": severity_id,
        "time": time_ms,
        "metadata": metadata,
        "action": action,
        "action_id": action_id,
        "api": {"operation": row.endpoint},
        "http_request": {"http_method": method or None, "url": {"path": row.endpoint}},
        "ai_agent": {"uid": str(row.agent_id)},
    }

    if row.agent_name:
        event["ai_agent"]["name"] = row.agent_name
    if row.user_id:
        event["actor"] = {"user": {"uid": str(row.user_id), "type_id": 1}}

    # Integrity seam (PR #1661): hash-chain provenance as an attestation object.
    # Prefer the per-org chain when present; fall back to the global chain.
    attestation: dict[str, Any] = {}
    if getattr(row, "entry_hash_org", None):
        attestation["entry_hash"] = row.entry_hash_org
        if getattr(row, "prev_hash_org", None):
            attestation["prev_entry_hash"] = row.prev_hash_org
        attestation["chain_uid"] = str(row.org_id)
    elif row.entry_hash:
        attestation["entry_hash"] = row.entry_hash
        if row.prev_hash:
            attestation["prev_entry_hash"] = row.prev_hash
    if attestation:
        event["attestation"] = attestation

    # Producer facts with no native OCSF home → unmapped (honest, not dropped).
    unmapped: dict[str, Any] = {}
    if row.latency_ms is not None:
        unmapped["latency_ms"] = row.latency_ms
    if row.cost_estimate_usd is not None:
        unmapped["cost_estimate_usd"] = float(row.cost_estimate_usd)
    if getattr(row, "org_chain_seq", None) is not None:
        unmapped["org_chain_seq"] = row.org_chain_seq
    md = row.request_metadata if isinstance(row.request_metadata, dict) else {}
    if "policy_version" in md:
        unmapped["policy_version"] = md["policy_version"]
    if unmapped:
        event["unmapped"] = unmapped

    return event
