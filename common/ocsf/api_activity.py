"""Map a gateway ``audit_log`` row to an OCSF **API Activity** event.

Grounded in AI Identity's OCSF contributions, not a hypothetical:
- **class_uid 6003 (API Activity)** with the **``ai_operation`` profile** — the
  shape a gateway/proxy can honestly populate (PR #1641: ``ai_agent`` placement).
- The **``attestation``** object (PR #1661 final shape, ``record_integrity``
  profile) carries the tamper-evident hash-chain linkage plus per-event
  signatures — so a consumer can verify provenance offline.
- Producer facts with no native OCSF home (policy version, latency, cost,
  org-chain sequence) go in ``unmapped`` — honest, per the OCSF guidance.

One audit_log row → one OCSF event. See docs/ocsf-pr1641-consumer-example.md
and docs/cosai-ws4-ocsf-mapping/CMF-OCSF-CROSSMAP.md for the source mapping.

Attestation shape notes (tracking #1661 @ fa4003ad):
- ``entry_hash`` / ``prev_entry_hash`` are OCSF ``fingerprint`` objects. The
  chain hashes are **HMAC-SHA-256** (keyed), so ``algorithm_id`` is 99 (Other)
  with the ``algorithm`` sibling naming it — claiming plain SHA-256 (id 3)
  would misstate the construction.
- ``signatures`` (required by the schema) carries an ECDSA-P256-SHA256
  signature computed over ``bytes.fromhex(entry_hash)`` — the same message
  convention Evidence Anchor's Merkle leaves use, so one verifier story
  covers both. OCSF's ``digital_signature`` object has no field for the
  signature bytes or key id; both ride in ``unmapped`` (``signature_b64``,
  ``signature_key_id``), matching the PR's reference example.
- When no signer is configured (some dev setups) the event is emitted
  without ``signatures`` — structurally final but not conformant to the
  required-field rule; production always signs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

OCSF_VERSION = "1.9.0-dev"

_HMAC_FINGERPRINT = {"algorithm_id": 99, "algorithm": "HMAC-SHA-256"}


@dataclass(frozen=True)
class EntrySignature:
    """A per-event signature produced by the export path.

    ``signature_b64`` is the base64 DER-encoded ECDSA-P256-SHA256 signature
    over ``bytes.fromhex(entry_hash)``; ``key_id`` matches the forensic
    signer's key identifier (KMS resource path or ``local:<sha256>``).
    """

    signature_b64: str
    key_id: str
    signed_time_ms: int


def select_chain(row: Any) -> tuple[str | None, str | None, str | None]:
    """Pick the chain the attestation describes: (entry_hash, prev, chain_uid).

    Prefers the per-org chain; falls back to the global chain. Single source
    of truth for both the emitter and the export signer, so the hash that is
    signed is always the hash that is displayed.
    """
    if getattr(row, "entry_hash_org", None):
        prev = getattr(row, "prev_hash_org", None) or None
        return row.entry_hash_org, prev, str(row.org_id)
    if row.entry_hash:
        return row.entry_hash, row.prev_hash or None, None
    return None, None, None


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
# Accept both the short form the gateway writes ("allow"/"deny") and the long
# form some writers/older rows use ("allowed"/"denied") so nothing falls through
# to Unknown just because of vocabulary drift.
_DECISION_ACTION: dict[str, tuple[int, str]] = {
    "allow": (1, "Allowed"),
    "allowed": (1, "Allowed"),
    "deny": (2, "Denied"),
    "denied": (2, "Denied"),
    "error": (99, "Other"),
}


def audit_log_to_ocsf(row: Any, entry_signature: EntrySignature | None = None) -> dict[str, Any]:
    """Transform an ``AuditLog`` ORM row into a single OCSF API Activity event.

    ``entry_signature``, when provided, must have been computed over
    ``bytes.fromhex(select_chain(row)[0])`` — the export path is responsible
    for signing the same hash this function displays.
    """
    method = (row.method or "").strip().upper()
    decision = (row.decision or "").strip().lower()
    activity_id = _METHOD_ACTIVITY.get(method, 0)
    action_id, action = _DECISION_ACTION.get(decision, (0, "Unknown"))

    # OCSF ``time`` is epoch milliseconds.
    time_ms = int(row.created_at.timestamp() * 1000) if row.created_at else None

    # severity_id: 3 Medium for a denied/errored action (more interesting to a
    # SOC) · 1 Informational otherwise (allowed, and unmapped/unknown — don't
    # alarm on vocabulary we didn't classify).
    severity_id = 3 if action_id in (2, 99) else 1

    entry_hash, prev_entry_hash, chain_uid = select_chain(row)

    profiles = ["ai_operation"]
    if entry_hash:
        # The attestation object is defined by the record_integrity profile
        # (#1661) — declare it whenever the object is emitted.
        profiles.append("record_integrity")
    metadata: dict[str, Any] = {"version": OCSF_VERSION, "profiles": profiles}
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

    # Gateway latency → OCSF base ``duration`` (milliseconds), its native home
    # (per the CMF↔OCSF crossmap) — not ``unmapped``.
    if row.latency_ms is not None:
        event["duration"] = row.latency_ms

    if row.agent_name:
        event["ai_agent"]["name"] = row.agent_name
    if row.user_id:
        event["actor"] = {"user": {"uid": str(row.user_id), "type_id": 1}}

    # Integrity seam (PR #1661 final shape): hash-chain provenance as an
    # attestation object under the record_integrity profile.
    if entry_hash:
        attestation: dict[str, Any] = {
            "uid": str(row.id),
            "entry_hash": {**_HMAC_FINGERPRINT, "value": entry_hash},
        }
        if prev_entry_hash:
            attestation["prev_entry_hash"] = {**_HMAC_FINGERPRINT, "value": prev_entry_hash}
        if chain_uid:
            attestation["chain_uid"] = chain_uid
        if entry_signature:
            attestation["signatures"] = [
                {
                    "algorithm_id": 3,  # ECDSA
                    "algorithm": "ECDSA-P256-SHA256",
                    "created_time": entry_signature.signed_time_ms,
                    "digest": {**_HMAC_FINGERPRINT, "value": entry_hash},
                }
            ]
        event["attestation"] = attestation

    # Producer facts with no native OCSF home → unmapped (honest, not dropped).
    # (latency has a native home: OCSF base ``duration``, set above.)
    unmapped: dict[str, Any] = {}
    if entry_hash and entry_signature:
        # OCSF's digital_signature object has no field for the signature bytes
        # or the key id — both ride unmapped, per the PR's reference example.
        unmapped["signature_b64"] = entry_signature.signature_b64
        unmapped["signature_key_id"] = entry_signature.key_id
    if row.cost_estimate_usd is not None:
        unmapped["cost_estimate_usd"] = float(row.cost_estimate_usd)
    if getattr(row, "org_chain_seq", None) is not None:
        unmapped["org_chain_seq"] = row.org_chain_seq
    md = row.request_metadata if isinstance(row.request_metadata, dict) else {}
    if "policy_version" in md:
        unmapped["policy_version"] = md["policy_version"]

    # Workload attestation (#423) — agent identity bound to a hardware root of
    # trust (mTLS cert first). This is the OCSF workload-attestation gap
    # (issues draft #5): no native OCSF home yet, so it rides ``unmapped``
    # honestly. Deliberately SEPARATE from the ``attestation`` object above,
    # which is record integrity (the hash chain) — different signals.
    if "attestation_type" in md:
        wa: dict[str, Any] = {"attestation_type": md["attestation_type"]}
        if "attestation_verified" in md:
            wa["verified"] = md["attestation_verified"]
        if md.get("attestation_subject"):
            wa["subject"] = md["attestation_subject"]
        if md.get("attestation_pubkey_sha256"):
            wa["public_key_sha256"] = md["attestation_pubkey_sha256"]
        unmapped["workload_attestation"] = wa

    if unmapped:
        event["unmapped"] = unmapped

    return event
