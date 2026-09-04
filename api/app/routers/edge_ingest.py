"""Edge deployment registration + OCSF audit ingest.

The inbound twin of the audit-forwarding sinks: an off-platform
enforcement point (Praxis/PPE running the cpex-ocsf-audit plugin)
registers once, gets a show-once ingest credential, and streams its
signed OCSF decision records to ``POST /api/v1/audit/ingest``.

Every record is verified on arrival — fingerprint recomputation, DSSE
signature, chain continuity, stream density — before it counts as
evidence. Failing records are stored quarantined with their reason,
never dropped: a gap is itself evidence. See
docs/specs/praxis-edge-enforcement.md (Component A).
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session  # noqa: TC002 — runtime Depends target

from api.app.auth import get_current_user
from api.app.routers.audit_sinks import _require_org_admin
from api.app.services.edge_ingest import STREAM_HEAD_SEQ, BatchVerifier, dedupe_key_for
from common.audit import create_audit_entry
from common.auth.keys import get_key_prefix, hash_key
from common.models import (
    Agent,
    EdgeAuditEvent,
    EdgeDeployment,
    EdgeEventStatus,
    EdgeStatus,
    User,
    get_db,
)
from common.schemas.edge import (
    EdgeCreate,
    EdgeCreatedResponse,
    EdgeListResponse,
    EdgeResponse,
    EdgeStreamSegment,
    EdgeStreamsResponse,
    IngestRecordResult,
    IngestResponse,
)

logger = logging.getLogger("ai_identity.api.edge_ingest")

router = APIRouter(prefix="/api/v1/edges", tags=["audit", "edges"])
ingest_router = APIRouter(prefix="/api/v1/audit", tags=["audit", "edges"])

EDGE_KEY_PREFIX = "aid_edge_"
MAX_BODY_BYTES = 5 * 1024 * 1024
MAX_BATCH_RECORDS = 1000


# ── Helpers ─────────────────────────────────────────────────────────


def _load_p256_public_key(pem: str):
    """Parse and validate an ECDSA P-256 public key PEM; 422 otherwise."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    try:
        key = load_pem_public_key(pem.encode())
    except Exception:
        raise HTTPException(
            status_code=422, detail="verify_key_pem is not a valid public key PEM"
        ) from None
    if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
        raise HTTPException(
            status_code=422,
            detail="verify_key_pem must be an ECDSA P-256 (secp256r1) public key",
        )
    return key


def _edge_lifecycle(db: Session, *, user: User, edge: EdgeDeployment, action: str) -> None:
    """Meta-audit row for edge lifecycle events (same pattern as sinks)."""
    agent = (
        db.query(Agent).filter(Agent.user_id == user.id).order_by(Agent.created_at.asc()).first()
    )
    if agent is None:
        logger.info("skipping %s meta-audit for user %s (no agent yet)", action, user.id)
        return
    create_audit_entry(
        db,
        agent_id=agent.id,
        endpoint=f"/api/v1/edges/{edge.id}",
        method="POST",
        decision="allow",
        request_metadata={"action_type": action, "resource_type": "edge_deployment"},
        user_id=user.id,
    )


def get_edge_deployment(
    request: Request,
    db: Session = Depends(get_db),
) -> EdgeDeployment:
    """Resolve the calling edge from ``Authorization: Bearer aid_edge_…``.

    401 for anything unrecognizable, 403 for a revoked edge — an edge
    credential never resolves to a user and grants nothing but ingest.
    """
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Edge ingest key required")
    token = auth[7:].strip()
    if not token.startswith(EDGE_KEY_PREFIX):
        raise HTTPException(status_code=401, detail="Edge ingest key required")
    edge = (
        db.query(EdgeDeployment).filter(EdgeDeployment.ingest_key_hash == hash_key(token)).first()
    )
    if edge is None:
        raise HTTPException(status_code=401, detail="Unknown edge ingest key")
    if edge.status != EdgeStatus.active:
        raise HTTPException(status_code=403, detail="Edge deployment is revoked")
    return edge


# ── Registration (Clerk-authenticated org admins) ───────────────────


@router.post("", response_model=EdgeCreatedResponse, status_code=201)
def register_edge(
    payload: EdgeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = _require_org_admin(db, user)
    _load_p256_public_key(payload.verify_key_pem)

    existing = (
        db.query(EdgeDeployment).filter(EdgeDeployment.chain_uid == payload.chain_uid).first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"chain_uid {payload.chain_uid!r} is already registered"
        )

    plaintext_key = EDGE_KEY_PREFIX + secrets.token_urlsafe(32)
    edge = EdgeDeployment(
        id=uuid.uuid4(),
        org_id=org_id,
        name=payload.name,
        chain_uid=payload.chain_uid,
        authority_uid=payload.authority_uid,
        verify_key_pem=payload.verify_key_pem,
        key_id=payload.key_id,
        ingest_key_hash=hash_key(plaintext_key),
        ingest_key_prefix=get_key_prefix(plaintext_key),
        status=EdgeStatus.active,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    _edge_lifecycle(db, user=user, edge=edge, action="edge_registered")

    resp = EdgeCreatedResponse.model_validate(
        {**EdgeResponse.model_validate(edge).model_dump(), "ingest_key": plaintext_key}
    )
    return resp


@router.get("", response_model=EdgeListResponse)
def list_edges(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = _require_org_admin(db, user)
    edges = (
        db.query(EdgeDeployment)
        .filter(EdgeDeployment.org_id == org_id)
        .order_by(EdgeDeployment.created_at.asc())
        .all()
    )
    return EdgeListResponse(edges=[EdgeResponse.model_validate(e) for e in edges])


@router.get("/{edge_id}/streams", response_model=EdgeStreamsResponse)
def edge_streams(
    edge_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evidence-continuity view of one edge's ingested stream.

    Ingest already verifies every arriving record and writes continuity
    anomalies on the rows — this is the read path for that work, which
    previously went nowhere a person could see it. Segments are grouped
    by (epoch, stream_id), the unit the emitter defines density over: a
    dense segment means no record in it was lost, and a NEW segment on
    the same stream is a producer restart — a boundary, not a loss. Two
    dense segments with a reset between them is the healthy shape of a
    stream that survived a crash.

    Quarantined rows are counted but never join a segment: their stamps
    are unauthenticated claims, so they can neither create nor repair
    density.
    """
    org_id = _require_org_admin(db, user)
    edge = (
        db.query(EdgeDeployment)
        .filter(EdgeDeployment.id == edge_id, EdgeDeployment.org_id == org_id)
        .first()
    )
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge deployment not found")

    status_counts = dict(
        db.query(EdgeAuditEvent.verification_status, func.count())
        .filter(EdgeAuditEvent.edge_id == edge.id)
        .group_by(EdgeAuditEvent.verification_status)
        .all()
    )

    rows = (
        db.query(
            EdgeAuditEvent.stream_id,
            EdgeAuditEvent.epoch,
            func.min(EdgeAuditEvent.stream_seq),
            func.max(EdgeAuditEvent.stream_seq),
            func.count(),
            func.count(EdgeAuditEvent.anomalies),
            func.max(EdgeAuditEvent.received_at),
        )
        .filter(
            EdgeAuditEvent.edge_id == edge.id,
            EdgeAuditEvent.verification_status == EdgeEventStatus.verified,
            EdgeAuditEvent.stream_id.isnot(None),
            EdgeAuditEvent.stream_seq.isnot(None),
        )
        .group_by(EdgeAuditEvent.stream_id, EdgeAuditEvent.epoch)
        .all()
    )
    segments = [
        EdgeStreamSegment(
            stream_id=stream_id,
            epoch=epoch,
            first_seq=first_seq,
            last_seq=last_seq,
            records=records,
            # Dense means nothing in the epoch was lost, and an epoch opens
            # at stream_seq 0 (AID-EMIT-1 §7; the reference host stamps from
            # a zero-initialised counter). Dedupe guarantees one row per
            # (stream, seq) identity, so the interior is dense when there are
            # exactly last-first+1 rows — but a segment that opens above 0
            # lost its head, and counting rows from wherever it starts would
            # score the one loss ingest flags as a `head gap` as dense. Both
            # verifiers (this and the offline validator) check the head, so
            # the read path has to agree with them.
            dense=first_seq == STREAM_HEAD_SEQ and records == last_seq - first_seq + 1,
            anomaly_records=anomaly_records,
            last_received_at=last_received_at,
        )
        for stream_id, epoch, first_seq, last_seq, records, anomaly_records, last_received_at in rows
    ]
    # Oldest epoch first within a stream, so restarts read in story order.
    segments.sort(key=lambda seg: (seg.stream_id, _epoch_key(seg.epoch)))

    return EdgeStreamsResponse(
        edge_id=edge.id,
        name=edge.name,
        chain_uid=edge.chain_uid,
        status=edge.status,
        last_ingest_at=edge.last_ingest_at,
        verified=status_counts.get(EdgeEventStatus.verified, 0),
        quarantined=status_counts.get(EdgeEventStatus.quarantined, 0),
        segments=segments,
    )


@router.post("/{edge_id}/revoke", response_model=EdgeResponse)
def revoke_edge(
    edge_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_id = _require_org_admin(db, user)
    edge = (
        db.query(EdgeDeployment)
        .filter(EdgeDeployment.id == edge_id, EdgeDeployment.org_id == org_id)
        .first()
    )
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge deployment not found")
    edge.status = EdgeStatus.revoked
    db.commit()
    db.refresh(edge)
    _edge_lifecycle(db, user=user, edge=edge, action="edge_revoked")
    return EdgeResponse.model_validate(edge)


# ── Ingest (edge-key authenticated) ─────────────────────────────────


@ingest_router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest_records(
    request: Request,
    edge: EdgeDeployment = Depends(get_edge_deployment),
    db: Session = Depends(get_db),
):
    """Verify and store an NDJSON batch of OCSF records from an edge.

    At-least-once friendly: a replayed record is reported ``duplicate``
    and not re-stored; batch order is verification order.
    """
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Batch exceeds 5 MiB")
    lines = [ln for ln in body.split(b"\n") if ln.strip()]
    if not lines:
        raise HTTPException(status_code=422, detail="Empty batch")
    if len(lines) > MAX_BATCH_RECORDS:
        raise HTTPException(status_code=413, detail=f"Batch exceeds {MAX_BATCH_RECORDS} records")

    parsed: list[tuple[dict | None, str | None]] = []
    for line in lines:
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("record is not a JSON object")
            parsed.append((event, None))
        except ValueError as exc:
            parsed.append((None, f"unparseable record: {exc}"))

    verifier = BatchVerifier(
        _load_p256_public_key(edge.verify_key_pem),
        expected_chain_uid=edge.chain_uid,
        expected_key_id=edge.key_id,
        **_chain_state(db, edge),
    )
    candidates = {k for event, _ in parsed if event for k in [dedupe_key_for(event)] if k}
    seen_keys = _known_dedupe_keys(db, edge, candidates)

    results: list[IngestRecordResult] = []
    counts = {"verified": 0, "quarantined": 0, "duplicates": 0, "errors": 0, "anomalies": 0}
    for event, parse_error in parsed:
        if event is None:
            counts["errors"] += 1
            results.append(IngestRecordResult(status="error", reason=parse_error))
            continue

        # Duplicates skip verification entirely: the stored row already
        # holds the outcome, and re-running check() would corrupt the
        # in-memory chain/stream state for the rest of the batch.
        key = dedupe_key_for(event)
        if key is not None and key in seen_keys:
            counts["duplicates"] += 1
            results.append(IngestRecordResult(dedupe_key=key, status="duplicate"))
            continue

        check = verifier.check(event)
        status = EdgeEventStatus.verified if check.verified else EdgeEventStatus.quarantined
        counts["verified" if check.verified else "quarantined"] += 1
        if check.anomalies:
            counts["anomalies"] += 1
        db.add(
            EdgeAuditEvent(
                org_id=edge.org_id,
                edge_id=edge.id,
                chain_uid=check.chain_uid,
                metadata_uid=check.metadata_uid,
                dedupe_key=check.dedupe_key,
                fingerprint=check.fingerprint,
                epoch=check.epoch,
                stream_id=check.stream_id,
                stream_seq=check.stream_seq,
                emission_seq=check.emission_seq,
                chain_position=check.chain_position,
                verification_status=status,
                failure_reason="; ".join(check.failures) or None,
                anomalies="; ".join(check.anomalies) or None,
                event=event,
            )
        )
        if check.dedupe_key is not None:
            seen_keys.add(check.dedupe_key)
        results.append(
            IngestRecordResult(
                uid=check.metadata_uid,
                dedupe_key=check.dedupe_key,
                status=status,
                reason="; ".join(check.failures) or None,
                anomalies="; ".join(check.anomalies) or None,
                chain_position=check.chain_position,
            )
        )
        if check.failures or check.anomalies:
            logger.warning(
                "%s edge record (edge=%s org=%s): %s",
                status if check.failures else "anomalous",
                edge.id,
                edge.org_id,
                "; ".join(check.failures + check.anomalies),
            )

    edge.last_ingest_at = datetime.now(UTC)
    db.commit()
    return IngestResponse(results=results, received=len(lines), **counts)


def _chain_state(db: Session, edge: EdgeDeployment) -> dict:
    """Resume-state for the verifier from previously stored rows.

    Duplicate detection must run against ALL of an edge's stored records
    (dedupe is a storage identity), but chain continuity resumes from the
    last VERIFIED row only — quarantined rows never become the head.
    """
    head_row = (
        db.query(EdgeAuditEvent)
        .filter(
            EdgeAuditEvent.edge_id == edge.id,
            EdgeAuditEvent.verification_status == EdgeEventStatus.verified,
        )
        .order_by(EdgeAuditEvent.id.desc())
        .first()
    )
    # Per stream, resume from its NEWEST epoch's tail — the density check
    # is scoped to (epoch, stream_id), so the max seq of an older epoch is
    # not this stream's tail any more. NULL epochs (rows from before the
    # column existed, or epoch-less producers) sort oldest, which keeps
    # legacy rows from shadowing a real epoch.
    tails: dict[str, tuple[int | None, int]] = {}
    seg_rows = (
        db.query(
            EdgeAuditEvent.stream_id,
            EdgeAuditEvent.epoch,
            func.max(EdgeAuditEvent.stream_seq),
        )
        .filter(
            EdgeAuditEvent.edge_id == edge.id,
            EdgeAuditEvent.stream_id.isnot(None),
            EdgeAuditEvent.verification_status == EdgeEventStatus.verified,
        )
        .group_by(EdgeAuditEvent.stream_id, EdgeAuditEvent.epoch)
        .all()
    )
    for stream_id, epoch, max_seq in seg_rows:
        held = tails.get(stream_id)
        if held is None or _epoch_key(epoch) > _epoch_key(held[0]):
            tails[stream_id] = (epoch, max_seq)

    # emission_seq resumes from the newest epoch seen on the edge, for the
    # same reason: it is the producer process's counter and died with it.
    emission_rows = (
        db.query(EdgeAuditEvent.epoch, func.max(EdgeAuditEvent.emission_seq))
        .filter(
            EdgeAuditEvent.edge_id == edge.id,
            EdgeAuditEvent.emission_seq.isnot(None),
            EdgeAuditEvent.verification_status == EdgeEventStatus.verified,
        )
        .group_by(EdgeAuditEvent.epoch)
        .all()
    )
    last_emission: tuple[int | None, int] | None = None
    for epoch, max_emission in emission_rows:
        if last_emission is None or _epoch_key(epoch) > _epoch_key(last_emission[0]):
            last_emission = (epoch, max_emission)
    return {
        "chain_head": (head_row.metadata_uid, head_row.fingerprint) if head_row else None,
        "chain_position": (head_row.chain_position or 0) if head_row else 0,
        "stream_tails": tails,
        "last_emission_seq": last_emission,
    }


def _epoch_key(epoch: int | None) -> tuple[int, int]:
    """Sort key that puts NULL/unknown epochs before any real one."""
    return (0, 0) if epoch is None else (1, epoch)


def _known_dedupe_keys(db: Session, edge: EdgeDeployment, candidates: set[str]) -> set[str]:
    """Which of this batch's identity keys are already stored for the edge."""
    if not candidates:
        return set()
    rows = (
        db.query(EdgeAuditEvent.dedupe_key)
        .filter(EdgeAuditEvent.edge_id == edge.id, EdgeAuditEvent.dedupe_key.in_(candidates))
        .all()
    )
    return {k for (k,) in rows}
