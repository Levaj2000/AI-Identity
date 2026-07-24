"""Public Evidence Anchor checkpoint feed — unauthenticated, CT-style.

Until now a signed checkpoint left our infrastructure only inside exported
Case File bundles (``evidence-anchor/checkpoints.json``), so "someone else
already holds the checkpoint" depended on a bundle having been distributed.
This feed publishes the checkpoint history itself, so the commitment is
public by default:

* ``GET /evidence-anchor/checkpoints`` — the append-only history of signed
  DSSE checkpoint envelopes, paginated, filterable by org and time range.
  Entries are exactly the artifact a bundle ships, so a bundle holder (or an
  independent mirror) can compare byte-for-byte.
* ``GET /evidence-anchor/checkpoints/{merkle_root}`` — the split-view spot
  check: given the root from a bundle, is that same signed checkpoint in the
  public history?

Public by design — no auth, same posture as the JWKS at
``/.well-known/ai-identity-public-keys.json``. What this exposes is the
commitment metadata only: opaque org UUIDs, batch sizes, id ranges, signing
times, and the signed envelopes (hashes + signatures). No event content, no
entry hashes beyond the signed root, no ``leaves``/``audit_log_ids``.

Ordering is ``(signed_at, id)`` ascending: history is append-only, so
ascending offset pages are stable and a mirror can resume with ``since``.
See ``docs/forensics/evidence-anchor-public-feed.md`` for the detection
story this feed + the GitHub mirror enable.
"""

from __future__ import annotations

import uuid  # noqa: TC003 — pydantic/FastAPI resolve these annotations at runtime
from datetime import datetime  # noqa: TC003 — same

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session  # noqa: TC002 — runtime db.query

from common.models import get_db
from common.models.audit_checkpoint import AuditCheckpoint

router = APIRouter(prefix="/evidence-anchor", tags=["forensics.anchor"])

# Completed history never changes (append-only), and the tip only advances on
# the ~15-min anchoring cadence — a short CDN TTL keeps the feed cheap to poll
# without meaningfully delaying a mirror.
_CACHE_CONTROL = "public, max-age=60"


class CheckpointFeedEntry(BaseModel):
    """One signed checkpoint, in the same shape a Case File bundle ships.

    ``merkle_root`` + ``envelope`` match a ``checkpoints.json`` entry exactly
    (byte-for-byte comparable); the remaining fields mirror values from inside
    the signed payload so consumers can filter without decoding it.
    """

    merkle_root: str
    envelope: dict
    org_id: uuid.UUID
    tree_size: int
    first_audit_id: int
    last_audit_id: int
    signer_key_id: str
    signed_at: datetime


class CheckpointFeedResponse(BaseModel):
    checkpoints: list[CheckpointFeedEntry]
    total: int = Field(description="Total checkpoints matching the filters, ignoring pagination.")
    limit: int
    offset: int


def _entry(cp: AuditCheckpoint) -> CheckpointFeedEntry:
    return CheckpointFeedEntry(
        merkle_root=cp.merkle_root,
        envelope=cp.envelope,
        org_id=cp.org_id,
        tree_size=cp.tree_size,
        first_audit_id=cp.first_audit_id,
        last_audit_id=cp.last_audit_id,
        signer_key_id=cp.signer_key_id,
        signed_at=cp.signed_at,
    )


@router.get(
    "/checkpoints",
    response_model=CheckpointFeedResponse,
    summary="Public Evidence Anchor checkpoint history",
    response_description=(
        "Signed Merkle checkpoint DSSE envelopes, oldest first. Each entry "
        "verifies offline against the JWKS at "
        "/.well-known/ai-identity-public-keys.json."
    ),
)
def list_checkpoints(
    response: Response,
    db: Session = Depends(get_db),
    org_id: uuid.UUID | None = Query(None, description="Restrict to one org's checkpoints."),
    since: datetime | None = Query(None, description="Only checkpoints signed at/after this time."),
    until: datetime | None = Query(None, description="Only checkpoints signed before this time."),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> CheckpointFeedResponse:
    """List signed checkpoints, oldest first.

    Ascending order over an append-only history means a page never shifts
    under a consumer: mirrors can walk ``offset`` forward, or poll with
    ``since`` set to the last ``signed_at`` they hold.
    """
    filters = []
    if org_id is not None:
        filters.append(AuditCheckpoint.org_id == org_id)
    if since is not None:
        filters.append(AuditCheckpoint.signed_at >= since)
    if until is not None:
        filters.append(AuditCheckpoint.signed_at < until)

    total = db.execute(select(func.count()).select_from(AuditCheckpoint).where(*filters)).scalar()
    rows = (
        db.execute(
            select(AuditCheckpoint)
            .where(*filters)
            .order_by(AuditCheckpoint.signed_at.asc(), AuditCheckpoint.id.asc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    response.headers["Cache-Control"] = _CACHE_CONTROL
    return CheckpointFeedResponse(
        checkpoints=[_entry(cp) for cp in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/checkpoints/{merkle_root}",
    response_model=CheckpointFeedEntry,
    summary="Look up one checkpoint by its Merkle root",
    response_description="The signed checkpoint committing to this root.",
    responses={404: {"description": "No published checkpoint carries this root."}},
)
def get_checkpoint(
    response: Response,
    merkle_root: str = Path(
        pattern="^[0-9a-f]{64}$",
        description="SHA-256 root (lowercase hex) from a bundle's checkpoints.json.",
    ),
    db: Session = Depends(get_db),
) -> CheckpointFeedEntry:
    """The split-view spot check.

    A bundle holder pastes the ``merkle_root`` their bundle verifies against;
    a 200 with the identical envelope proves the checkpoint they hold is the
    same one in the public history — i.e. they weren't shown a private fork.
    A 404 on a root that verifies offline is the red flag worth escalating.
    """
    cp = (
        db.execute(
            select(AuditCheckpoint)
            .where(AuditCheckpoint.merkle_root == merkle_root)
            .order_by(AuditCheckpoint.signed_at.asc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if cp is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No published checkpoint carries this merkle_root. If a bundle in "
                "your possession verifies against it offline, treat the mismatch "
                "as a split-view signal and contact security@ai-identity.co."
            ),
        )
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return _entry(cp)
