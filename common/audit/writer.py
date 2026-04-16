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
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.audit.correlation import (
    CORRELATION_ID_MAX_LEN,
    get_current_correlation_id,
)
from common.audit.sanitizer import V1_STRUCTURED_KEYS, sanitize_metadata
from common.config.settings import settings
from common.models.audit_log import AuditLog
from common.schemas.audit_metadata import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    AuditMetadataV1,
    as_metadata_dict,
)

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


def _ensure_system_org(db: Session) -> uuid.UUID:
    """Return the sentinel system org ID, creating it if absent.

    The system org is the fallback tenant for audit entries that can't
    be attributed to a real org (shadow agents, pre-auth errors). This
    lets us enforce `audit_log.org_id NOT NULL` while still logging
    orphan traffic for platform admins to investigate.

    Idempotent — safe to call on every write.
    """
    from common.models.organization import (
        SYSTEM_ORG_ID,
        SYSTEM_ORG_NAME,
        SYSTEM_USER_EMAIL,
        SYSTEM_USER_ID,
        Organization,
    )
    from common.models.user import User

    org = db.query(Organization).filter(Organization.id == SYSTEM_ORG_ID).first()
    if org is not None:
        return SYSTEM_ORG_ID

    # Ensure the system user exists first (owner_id is NOT NULL on orgs)
    sys_user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
    if sys_user is None:
        sys_user = User(
            id=SYSTEM_USER_ID,
            email=SYSTEM_USER_EMAIL,
            role="system",
            tier="enterprise",
        )
        db.add(sys_user)
        db.flush()

    db.add(
        Organization(
            id=SYSTEM_ORG_ID,
            name=SYSTEM_ORG_NAME,
            owner_id=SYSTEM_USER_ID,
            tier="enterprise",
        )
    )
    db.flush()
    return SYSTEM_ORG_ID


def create_audit_entry(
    db: Session,
    *,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    decision: str,
    cost_estimate_usd: float | None = None,
    latency_ms: int | None = None,
    request_metadata: AuditMetadataV1 | dict[str, Any] | None = None,
    user_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
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

    TENANCY: org_id is resolved from the agent; for shadow/orphan entries
    with no registered agent, the sentinel system org is used so the row
    still has a NOT NULL org_id.

    TRACING: correlation_id is auto-resolved from the request contextvar
    when not passed explicitly. Pass ``correlation_id=...`` from
    background jobs (no request in scope) to keep the cross-service
    trace intact.

    METADATA SHAPE: ``request_metadata`` may be a plain dict (legacy
    callers) or an ``AuditMetadataV1`` instance (preferred for new code).
    V1 instances are dumped and tagged with ``schema_version=1``; plain
    dicts pass through untagged — readers treat untagged rows as pre-v1.
    """
    # Caller may pass an AuditMetadataV1 instance (preferred) or a plain dict
    # (legacy). The typed path skips the flat-value sanitizer for its known
    # structured sub-dicts — Pydantic already validated the shape.
    is_typed = isinstance(request_metadata, AuditMetadataV1)
    metadata_dict = as_metadata_dict(request_metadata)

    # If the caller passed an AuditMetadataV1 with a correlation_id baked in,
    # promote it so the top-level column stays in sync with the blob.
    if correlation_id is None and metadata_dict.get("correlation_id"):
        candidate = metadata_dict["correlation_id"]
        if isinstance(candidate, str) and 0 < len(candidate) <= CORRELATION_ID_MAX_LEN:
            correlation_id = candidate

    # Fall back to the per-request contextvar set by the HTTP middleware.
    # Background jobs with no request in scope get None — still valid.
    if correlation_id is None:
        correlation_id = get_current_correlation_id()

    # Stamp the v1 schema tag on any metadata that explicitly carries a
    # ``correlation_id`` key — that signals the caller intended structured
    # metadata. We don't retroactively stamp opaque legacy dicts just
    # because the middleware set a contextvar.
    if (
        correlation_id
        and metadata_dict
        and "correlation_id" in metadata_dict
        and SCHEMA_VERSION_KEY not in metadata_dict
    ):
        metadata_dict[SCHEMA_VERSION_KEY] = CURRENT_SCHEMA_VERSION

    # Sanitize metadata — allowlist only, PII blocked. Typed v1 instances
    # also keep their Pydantic-validated structured sub-dicts intact.
    metadata = sanitize_metadata(
        metadata_dict,
        trusted_structured_keys=V1_STRUCTURED_KEYS if is_typed else frozenset(),
    )

    # Resolve user_id, agent_name, and org_id from agent
    # (for RLS tenant isolation + denormalization)
    agent_name: str | None = None
    org_id: uuid.UUID | None = None
    from common.models.agent import Agent

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent:
        agent_name = agent.name
        org_id = agent.org_id
        if user_id is None:
            user_id = agent.user_id

    # Shadow / orphan fallback: no registered agent OR agent without an org.
    # Route the entry to the sentinel system org so org_id stays NOT NULL.
    if org_id is None:
        org_id = _ensure_system_org(db)

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
        org_id=org_id,
        correlation_id=correlation_id,
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
    db.flush()  # assign entry.id before enqueuing outbox rows

    # Enqueue forwarding (Phase 2A). No-op when no sinks are configured,
    # which is the common case today. Any failure here is isolated to the
    # outbox row itself and MUST NOT change the audit-write outcome — if
    # the outbox system is broken, the audit trail is still intact.
    try:
        from common.audit.outbox import enqueue_for_sinks

        enqueue_for_sinks(db, audit_entry=entry)
    except Exception:
        # The audit row is already flushed; its integrity is independent of
        # forwarding. Log and proceed — the DB rollback would undo the
        # audit write itself, which is worse than losing a forwarded copy.
        import logging

        logging.getLogger("ai_identity.audit.writer").exception(
            "outbox enqueue failed for audit_log.id=%s — event recorded but not forwarded",
            entry.id,
        )

    db.commit()
    db.refresh(entry)

    # Phase 2B — Prometheus observability. Also opportunistic / never raises:
    # a metrics-subsystem hiccup must never change the audited outcome.
    try:
        from common.observability.metrics import record_audit_write

        record_audit_write(
            decision=decision,
            deny_reason=(metadata.get("deny_reason") if isinstance(metadata, dict) else None),
            latency_ms=latency_ms,
        )
    except Exception:
        import logging

        logging.getLogger("ai_identity.audit.writer").warning(
            "metric emission failed for audit_log.id=%s", entry.id, exc_info=True
        )

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
