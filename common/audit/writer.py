"""Append-only audit log writer with HMAC-SHA256 integrity chain.

Every audit entry is linked to the previous entry via an HMAC chain:
  entry_hash = HMAC-SHA256(canonical_data + prev_hash, key=AUDIT_HMAC_KEY)

The chain is global (not per-agent) — any deleted or modified row in the
entire table breaks the chain, providing the strongest tamper-evidence
guarantee for SOC 2 compliance.
"""

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.audit.sanitizer import sanitize_metadata
from common.config.settings import settings
from common.models.audit_log import AuditLog

GENESIS = "GENESIS"


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC).

    SQLite returns naive datetimes; PostgreSQL returns aware ones.
    This normalizes both to UTC-aware for consistent hashing.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ── Hash Computation ─────────────────────────────────────────────────────


def _canonical_payload(
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    decision: str,
    cost_estimate_usd: float | None,
    latency_ms: int | None,
    request_metadata: dict,
    created_at: datetime,
    prev_hash: str,
) -> str:
    """Build a deterministic JSON string of all data fields for hashing.

    Uses sort_keys + compact separators for canonical form.
    UUIDs → str, datetimes → isoformat, Decimals → str.
    """
    payload = {
        "agent_id": str(agent_id),
        "cost_estimate_usd": str(cost_estimate_usd) if cost_estimate_usd is not None else None,
        "created_at": created_at.isoformat(),
        "decision": decision,
        "endpoint": endpoint,
        "latency_ms": latency_ms,
        "method": method,
        "prev_hash": prev_hash,
        "request_metadata": request_metadata,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_entry_hash(
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    decision: str,
    cost_estimate_usd: float | None,
    latency_ms: int | None,
    request_metadata: dict,
    created_at: datetime,
    prev_hash: str,
    hmac_key: str | None = None,
) -> str:
    """Compute HMAC-SHA256 of the canonical payload.

    Returns the hex-encoded digest (64 characters).
    """
    key = (hmac_key or settings.audit_hmac_key).encode("utf-8")
    message = _canonical_payload(
        agent_id,
        endpoint,
        method,
        decision,
        cost_estimate_usd,
        latency_ms,
        request_metadata,
        created_at,
        prev_hash,
    ).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


# ── Audit Entry Writer ───────────────────────────────────────────────────


def _get_last_hash(db: Session) -> str:
    """Get the entry_hash of the most recent audit log entry.

    Uses SELECT … FOR UPDATE on PostgreSQL to serialize concurrent writers.
    Returns GENESIS if the table is empty.
    """
    dialect = db.bind.dialect.name if db.bind else "unknown"

    stmt = select(AuditLog.entry_hash).order_by(AuditLog.id.desc()).limit(1)

    if dialect == "postgresql":
        stmt = stmt.with_for_update()

    result = db.execute(stmt).scalar_one_or_none()
    return result if result is not None else GENESIS


def create_audit_entry(
    db: Session,
    *,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    decision: str,
    cost_estimate_usd: float | None = None,
    latency_ms: int | None = None,
    request_metadata: dict | None = None,
    user_id: uuid.UUID | None = None,
) -> AuditLog:
    """Create a new audit log entry with HMAC integrity chain.

    1. Sanitizes request_metadata (allowlist-only, PII-blocked)
    2. Gets the previous entry's hash (or GENESIS for the first entry)
    3. Sets created_at explicitly in Python (included in hash)
    4. Computes the HMAC-SHA256 entry_hash
    5. INSERTs the row
    6. Optionally writes a PII-redacted debug log entry
    7. Returns the committed AuditLog instance

    SECURITY: request_metadata is sanitized BEFORE hashing. Only allowed
    metadata keys are stored. PII fields are rejected with a warning.
    """
    # Sanitize metadata — allowlist only, PII blocked
    metadata = sanitize_metadata(request_metadata)

    # Resolve user_id and agent_name from agent (for RLS tenant isolation + denormalization)
    agent_name: str | None = None
    from common.models.agent import Agent

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent:
        agent_name = agent.name
        if user_id is None:
            user_id = agent.user_id

    # Opt-in debug logging (PII-redacted, separate from audit trail)
    from common.audit.debug_log import write_debug_entry

    write_debug_entry(
        agent_id=str(agent_id),
        endpoint=endpoint,
        method=method,
        decision=decision,
        raw_metadata=request_metadata,
    )

    # Resolve the org's per-tenant forensic_verify_key (fall back to global key if absent)
    org_hmac_key: str | None = None
    if agent and agent.org_id:
        from common.models.organization import Organization

        org = db.query(Organization).filter(Organization.id == agent.org_id).first()
        if org and org.forensic_verify_key:
            org_hmac_key = org.forensic_verify_key

    now = datetime.now(UTC)
    prev_hash = _get_last_hash(db)

    entry_hash = compute_entry_hash(
        agent_id=agent_id,
        endpoint=endpoint,
        method=method,
        decision=decision,
        cost_estimate_usd=cost_estimate_usd,
        latency_ms=latency_ms,
        request_metadata=metadata,
        created_at=now,
        prev_hash=prev_hash,
        hmac_key=org_hmac_key,
    )

    entry = AuditLog(
        agent_id=agent_id,
        user_id=user_id,
        agent_name=agent_name,
        endpoint=endpoint,
        method=method,
        decision=decision,
        cost_estimate_usd=cost_estimate_usd,
        latency_ms=latency_ms,
        request_metadata=metadata,
        created_at=now,
        entry_hash=entry_hash,
        prev_hash=prev_hash,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ── Report Signature ─────────────────────────────────────────────────────


def generate_report_signature(
    report_id: str,
    generated_at: datetime,
    chain_valid: bool,
    total_entries: int,
    entries_verified: int,
    hmac_key: str | None = None,
) -> str:
    """Generate an HMAC-SHA256 signature for a forensics report.

    Signs a canonical JSON payload of the report's identity and chain
    verification result. The recipient can recompute this signature to
    confirm the report was produced by AI Identity and has not been
    modified since export.

    The signed fields are intentionally minimal — they capture what
    matters for chain-of-custody (who generated it, when, and whether
    the chain was intact) without tying the signature to mutable content
    like event lists that may be filtered or redacted during review.
    """
    key = (hmac_key or settings.audit_hmac_key).encode("utf-8")
    payload = json.dumps(
        {
            "entries_verified": entries_verified,
            "chain_valid": chain_valid,
            "generated_at": _ensure_utc(generated_at).isoformat(),
            "report_id": report_id,
            "total_entries": total_entries,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_report_signature(
    report_id: str,
    generated_at: datetime,
    chain_valid: bool,
    total_entries: int,
    entries_verified: int,
    signature: str,
    hmac_key: str | None = None,
) -> bool:
    """Verify a forensics report signature.

    Returns True if the signature is valid — i.e., the report was generated
    by AI Identity and the identity/chain fields have not been altered
    since export. Uses a constant-time comparison to prevent timing attacks.
    """
    expected = generate_report_signature(
        report_id=report_id,
        generated_at=generated_at,
        chain_valid=chain_valid,
        total_entries=total_entries,
        entries_verified=entries_verified,
        hmac_key=hmac_key,
    )
    return hmac.compare_digest(expected, signature)


# ── Chain Verification ───────────────────────────────────────────────────


@dataclass
class ChainVerificationResult:
    """Result of an integrity chain verification."""

    valid: bool
    total_entries: int
    entries_verified: int
    first_broken_id: int | None = None
    message: str = ""


def verify_chain(
    db: Session,
    *,
    hmac_key: str | None = None,
    agent_id: uuid.UUID | None = None,
    batch_size: int = 1000,
) -> ChainVerificationResult:
    """Walk the audit log and verify the HMAC chain.

    For each entry (ordered by id ASC):
    1. Checks prev_hash matches the previous entry's entry_hash
       (or GENESIS for the first entry)
    2. Recomputes the HMAC and checks it matches entry_hash

    Args:
        db: Database session.
        hmac_key: Override HMAC key (for testing).
        agent_id: If provided, verify hash integrity for this agent's
            entries only (no chain linkage — chain is global).
        batch_size: Entries per query for memory efficiency.

    Returns:
        ChainVerificationResult with valid=True if chain is intact.
    """
    query = db.query(AuditLog).order_by(AuditLog.id.asc())
    if agent_id:
        query = query.filter(AuditLog.agent_id == agent_id)

    total = query.count()
    if total == 0:
        return ChainVerificationResult(
            valid=True,
            total_entries=0,
            entries_verified=0,
            message="No entries to verify",
        )

    # Build a cache of agent_id → org forensic_verify_key so we use the
    # same key that was used when the entry was created.
    _org_key_cache: dict[uuid.UUID, str | None] = {}

    def _resolve_hmac_key(entry_agent_id: uuid.UUID) -> str | None:
        """Return the per-org HMAC key for an agent, or None for the global key."""
        if hmac_key is not None:
            return hmac_key  # explicit override (testing)
        if entry_agent_id in _org_key_cache:
            return _org_key_cache[entry_agent_id]
        from common.models.agent import Agent as AgentModel
        from common.models.organization import Organization

        agent = db.query(AgentModel).filter(AgentModel.id == entry_agent_id).first()
        key = None
        if agent and agent.org_id:
            org = db.query(Organization).filter(Organization.id == agent.org_id).first()
            if org and org.forensic_verify_key:
                key = org.forensic_verify_key
        _org_key_cache[entry_agent_id] = key
        return key

    expected_prev_hash = GENESIS
    verified = 0
    offset = 0

    while offset < total:
        entries = query.offset(offset).limit(batch_size).all()
        if not entries:
            break

        for entry in entries:
            # Check prev_hash linkage (global chain only, not per-agent filter)
            if not agent_id and entry.prev_hash != expected_prev_hash:
                return ChainVerificationResult(
                    valid=False,
                    total_entries=total,
                    entries_verified=verified,
                    first_broken_id=entry.id,
                    message=(
                        f"Chain broken at entry {entry.id}: "
                        f"expected prev_hash={expected_prev_hash!r}, "
                        f"got {entry.prev_hash!r}"
                    ),
                )

            # Recompute the HMAC (normalize timezone for SQLite compat)
            hash_kwargs = dict(
                agent_id=entry.agent_id,
                endpoint=entry.endpoint,
                method=entry.method,
                decision=entry.decision,
                cost_estimate_usd=(
                    float(entry.cost_estimate_usd) if entry.cost_estimate_usd is not None else None
                ),
                latency_ms=entry.latency_ms,
                request_metadata=entry.request_metadata,
                created_at=_ensure_utc(entry.created_at),
                prev_hash=entry.prev_hash,
            )

            entry_hmac_key = _resolve_hmac_key(entry.agent_id)
            recomputed = compute_entry_hash(**hash_kwargs, hmac_key=entry_hmac_key)

            # Entries created before the per-org key was configured were
            # signed with the global key.  If the org key doesn't match,
            # retry with the global key (hmac_key=None) before failing.
            if recomputed != entry.entry_hash and entry_hmac_key is not None:
                recomputed = compute_entry_hash(**hash_kwargs, hmac_key=None)

            if recomputed != entry.entry_hash:
                return ChainVerificationResult(
                    valid=False,
                    total_entries=total,
                    entries_verified=verified,
                    first_broken_id=entry.id,
                    message=(
                        f"Hash mismatch at entry {entry.id}: "
                        f"recomputed={recomputed!r}, "
                        f"stored={entry.entry_hash!r}"
                    ),
                )

            expected_prev_hash = entry.entry_hash
            verified += 1

        offset += batch_size

    return ChainVerificationResult(
        valid=True,
        total_entries=total,
        entries_verified=verified,
        message="Chain integrity verified",
    )
