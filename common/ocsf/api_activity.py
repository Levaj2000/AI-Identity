"""Map a gateway ``audit_log`` row to an OCSF **API Activity** event.

Grounded in AI Identity's OCSF contributions, not a hypothetical:
- **class_uid 6003 (API Activity)** with the **``ai_operation`` profile** — the
  shape a gateway/proxy can honestly populate (PR #1641: ``ai_agent`` placement).
- The **``attestation``** object (PR #1661, MERGED into OCSF 1.9 on
  2026-07-17, ocsf-schema ``2a244bc9``) carried on the ``record_integrity``
  profile's ``attestation_list`` — the tamper-evident hash-chain linkage plus
  per-event signatures, so a consumer can verify provenance offline.
- Producer facts with no native OCSF home (policy version, latency, cost,
  org-chain sequence) go in ``unmapped`` — honest, per the OCSF guidance.

One audit_log row → one OCSF event. See docs/ocsf-pr1641-consumer-example.md
and docs/cosai-ws4-ocsf-mapping/CMF-OCSF-CROSSMAP.md for the source mapping.

Attestation shape notes (#1661 merged shape):
- The ``record_integrity`` profile carries ``attestation_list`` — an **array**
  of ``attestation`` objects (independent attesters each contribute one entry;
  the gateway is a single attester, so it emits a one-element list).
- ``fingerprint`` is an OCSF ``fingerprint`` object. The chain hashes are
  **HMAC-SHA-256** (keyed), so ``algorithm_id`` is 99 (Other) with the
  ``algorithm`` sibling naming it — claiming plain SHA-256 (id 3) would
  misstate the construction. ``encoding_id`` 1 names the Hex value encoding
  (#1684). ``serialization_id`` is 99 (Other) with the ``serialization``
  sibling naming the producer scheme: the fingerprinted input is the chain
  writer's sorted-compact JSON payload + prev hash — not RFC 8785 JCS, so
  claiming JCS (2) would misstate it.
- ``prev_event`` is the merged Previous Event object: ``uid`` (required — the
  predecessor's ``metadata.uid``), ``type_uid`` (recommended), and
  ``fingerprint`` (the predecessor's own chain fingerprint, which binds the
  reference to content). Every event emits ``metadata.uid`` so these
  references resolve. The export path supplies the predecessor locator via
  ``PrevEventRef``; when the predecessor row is unknown (e.g. beyond
  retention) ``prev_event`` is omitted — ``uid`` is required, so a
  locator-less object would not validate. The chain's genesis row (stored
  sentinel ``"GENESIS"``) has no predecessor and omits ``prev_event``.
- ``signatures`` carries an ECDSA-P256-SHA256 signature computed over
  ``bytes.fromhex(entry_hash)`` — a flat byte sequence, so
  ``serialization_id`` is 1 (``Flat``; note the final-round renumber — JCS is
  2). Same message convention as Evidence Anchor's Merkle leaves, so one
  verifier story covers both. OCSF's ``digital_signature`` object still has
  no field for the signature bytes or key id; both ride in ``unmapped``
  (``signature_b64``, ``signature_key_id``) pending the upstream follow-on.
- When no signer is configured (some dev setups) the event is emitted without
  ``signatures`` — the schema's ``at_least_one(fingerprint, signatures)``
  constraint still holds via ``fingerprint``; production always signs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

OCSF_VERSION = "1.9.0-dev"

# Chain fingerprints, everywhere they appear (attestation.fingerprint,
# prev_event.fingerprint, signature digest): keyed HMAC (algorithm Other + a
# sibling naming it), hex-encoded value, producer-defined serialization named
# by the sibling (sorted-compact JSON payload + prev hash — not RFC 8785).
_HMAC_FINGERPRINT = {
    "algorithm_id": 99,
    "algorithm": "HMAC-SHA-256",
    "encoding_id": 1,  # Hex
    "serialization_id": 99,
    "serialization": "AI-Identity audit chain v1 (sorted-compact JSON + prev hash)",
}

# The chain writer (common/audit/writer.py) stores this literal sentinel as
# prev_hash / prev_hash_org on a chain's first row. In OCSF terms that is a
# missing predecessor, not a hash — passing it through would emit a
# fingerprint whose value isn't a hash, so the genesis event omits
# ``prev_event`` instead. (Not imported from the writer: this module
# stays free of ORM/settings dependencies.)
_GENESIS = "GENESIS"


def _prev_or_none(value: Any) -> str | None:
    return None if not value or value == _GENESIS else value


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


@dataclass(frozen=True)
class PrevEventRef:
    """Locator for a row's chain predecessor, resolved by the export path.

    ``uid`` is the predecessor's ``metadata.uid`` (its audit row id) —
    required by the merged ``prev_event`` object. ``type_uid`` is the
    predecessor's event type, directing a consumer to the store where it
    resides. The fingerprint half of ``prev_event`` comes from the row's own
    stored prev hash; only the locator needs external resolution.
    """

    uid: str
    type_uid: int


def select_chain(row: Any) -> tuple[str | None, str | None, str | None]:
    """Pick the chain the attestation describes: (entry_hash, prev, chain_uid).

    Prefers the per-org chain; falls back to the global chain. Single source
    of truth for both the emitter and the export signer, so the hash that is
    signed is always the hash that is displayed.

    The GENESIS sentinel on a chain's first row maps to ``None`` — the genesis
    event has no predecessor to reference.
    """
    if getattr(row, "entry_hash_org", None):
        prev = _prev_or_none(getattr(row, "prev_hash_org", None))
        return row.entry_hash_org, prev, str(row.org_id)
    if row.entry_hash:
        return row.entry_hash, _prev_or_none(row.prev_hash), None
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


def event_type_uid(method: str | None) -> int:
    """The API Activity ``type_uid`` for an audit row's HTTP method.

    Shared with the export path so ``prev_event.type_uid`` is derived the
    same way as the event's own ``type_uid``.
    """
    return 6003 * 100 + _METHOD_ACTIVITY.get((method or "").strip().upper(), 0)


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


def audit_log_to_ocsf(
    row: Any,
    entry_signature: EntrySignature | None = None,
    prev_event_ref: PrevEventRef | None = None,
) -> dict[str, Any]:
    """Transform an ``AuditLog`` ORM row into a single OCSF API Activity event.

    ``entry_signature``, when provided, must have been computed over
    ``bytes.fromhex(select_chain(row)[0])`` — the export path is responsible
    for signing the same hash this function displays.

    ``prev_event_ref``, when provided, must locate the chain predecessor whose
    hash is this row's stored prev hash — the export path resolves it (in-set
    map + DB fallback). Without it, ``prev_event`` is omitted even when a prev
    hash exists, because ``prev_event.uid`` is required.
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
        # The attestation_list attribute is defined by the record_integrity
        # profile (#1661) — declare it whenever attestations are emitted.
        profiles.append("record_integrity")
    # metadata.uid: every event carries its identity so prev_event.uid
    # references resolve across an export (and across runtimes).
    metadata: dict[str, Any] = {
        "uid": str(row.id),
        "version": OCSF_VERSION,
        "profiles": profiles,
    }
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

    # Integrity seam (#1661 merged shape): hash-chain provenance as a
    # one-element attestation_list under the record_integrity profile.
    if entry_hash:
        attestation: dict[str, Any] = {
            "uid": str(row.id),
            "fingerprint": {**_HMAC_FINGERPRINT, "value": entry_hash},
        }
        if prev_entry_hash and prev_event_ref:
            attestation["prev_event"] = {
                "uid": prev_event_ref.uid,
                "type_uid": prev_event_ref.type_uid,
                "fingerprint": {**_HMAC_FINGERPRINT, "value": prev_entry_hash},
            }
        if chain_uid:
            attestation["chain_uid"] = chain_uid
        if entry_signature:
            attestation["signatures"] = [
                {
                    "algorithm_id": 3,  # ECDSA
                    "algorithm": "ECDSA-P256-SHA256",
                    # The signature is over the raw hash bytes — no envelope,
                    # no canonicalization of structured data: Flat (1).
                    "serialization_id": 1,
                    "serialization": "Flat",
                    "created_time": entry_signature.signed_time_ms,
                    "digest": {**_HMAC_FINGERPRINT, "value": entry_hash},
                }
            ]
        event["attestation_list"] = [attestation]

    # Producer facts with no native OCSF home → unmapped (honest, not dropped).
    # (latency has a native home: OCSF base ``duration``, set above.)
    unmapped: dict[str, Any] = {}
    if entry_hash and entry_signature:
        # OCSF's digital_signature object has no field for the signature bytes
        # or the key id — both ride unmapped, per the PR's reference example.
        unmapped["signature_b64"] = entry_signature.signature_b64
        unmapped["signature_key_id"] = entry_signature.key_id
    if prev_entry_hash and not prev_event_ref:
        # Predecessor locator unknown (beyond retention / unresolvable):
        # prev_event needs its required uid, so the bare linkage hash rides
        # unmapped rather than being silently dropped.
        unmapped["prev_entry_hash"] = prev_entry_hash
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
    # honestly. Deliberately SEPARATE from the ``attestation_list`` above,
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

    # Mandate lifecycle (issue / spend / exceed / revoke) — the monetary-
    # authority story: which signed grant this event acted under, the amount,
    # and the cumulative spend vs limit. This is delegated-authority context
    # (issues draft #6 territory); no native OCSF home yet, so it rides
    # ``unmapped`` as one coherent block. Amounts are integer cents.
    if md.get("resource_type") == "mandate" and md.get("mandate_id"):
        mandate_block: dict[str, Any] = {"mandate_id": md["mandate_id"]}
        if md.get("action_type"):
            mandate_block["action"] = md["action_type"]
        for src, dst in (
            ("spend_amount_cents", "amount_cents"),
            ("spend_currency", "currency"),
            ("mandate_spent_cents", "spent_cents"),
            ("mandate_limit_cents", "limit_cents"),
            ("spend_settlement", "settlement"),
            ("spend_reference", "reference"),
            ("deny_reason", "deny_reason"),
        ):
            if md.get(src) is not None:
                mandate_block[dst] = md[src]
        unmapped["mandate"] = mandate_block

    if unmapped:
        event["unmapped"] = unmapped

    return event
