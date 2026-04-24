"""Per-row signing for change_log v2 exports.

See [docs/specs/change-log-export-schema-v2.md](../../docs/specs/change-log-export-schema-v2.md)
for the column contract. This module only deals with the cryptographic
payload — the builder in ``common.compliance.builders.soc2`` handles
column layout and CSV emission.

The signing model mirrors DSSE: a row is signed over
``PAE(CHANGE_LOG_ROW_PAYLOAD_TYPE, canonical_json_bytes)``. A domain-
separated payload type means a change_log row signature cannot be
replayed as a manifest or attestation signature and vice versa.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import rfc8785

from common.schemas.forensic_attestation import pae

if TYPE_CHECKING:
    from common.forensic.signer import SignerHandle


# Domain-separated payload type. Must not collide with attestation or
# manifest types — the PAE construction guarantees cross-type signatures
# cannot replay, but keeping the strings distinct makes verifier errors
# readable.
CHANGE_LOG_ROW_PAYLOAD_TYPE = "application/vnd.ai-identity.change-log-row+json"

# Field order inside the signed payload. Must match
# scripts/verify_change_log.py exactly or signatures won't verify.
# RFC 8785 JCS sorts keys lexicographically at serialization time, so
# the order of this list is documentation rather than a wire format
# contract — but we keep it pinned so reviewers see the canonical set.
SIGNED_FIELDS: tuple[str, ...] = (
    "audit_log_id",
    "created_at",
    "action_type",
    "resource_type",
    "agent_id",
    "actor_user_id",
    "decision",
    "decision_reason",
    "policy_version",
    "entry_hash",
    "prev_hash",
    "diff_json",
    "details_json",
)


def build_signed_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Project ``row`` to the subset of fields covered by the signature.

    Display-only and source-context fields (``agent_name``,
    ``actor_email``, ``ip_address`` etc.) are intentionally excluded so
    redacting them post-export does not invalidate the signature.
    """
    payload: dict[str, Any] = {}
    for field in SIGNED_FIELDS:
        value = row.get(field, "")
        if field in {"diff_json", "details_json"}:
            # These two are JSON objects in the signed payload, not
            # strings — the CSV representation stringifies them but
            # the signature covers the structural form.
            payload[field] = value if isinstance(value, (dict, list)) else {}
        else:
            payload[field] = value
    return payload


def canonical_row_bytes(row: dict[str, Any]) -> bytes:
    """RFC 8785 JCS bytes of the signed payload — exact signing input body."""
    return rfc8785.dumps(build_signed_payload(row))


def signing_input(row: dict[str, Any]) -> bytes:
    """DSSE PAE of the canonical payload. What the signer's key actually signs."""
    return pae(CHANGE_LOG_ROW_PAYLOAD_TYPE, canonical_row_bytes(row))


def sign_row(row: dict[str, Any], signer: SignerHandle) -> tuple[str, str]:
    """Sign a change_log row → (base64 signature, signer key id).

    The base64 signature and key id are emitted as the ``signature`` and
    ``signing_key_id`` CSV columns respectively. Both are strings so
    they round-trip cleanly through any CSV consumer.
    """
    signature_der = signer.sign(signing_input(row))
    return base64.b64encode(signature_der).decode("ascii"), signer.key_id
