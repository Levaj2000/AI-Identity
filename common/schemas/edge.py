"""Pydantic schemas for edge deployment registration and OCSF ingest."""

from __future__ import annotations

import datetime  # noqa: TC003 — used by Pydantic at model-build time
import uuid  # noqa: TC003 — used by Pydantic at model-build time

from pydantic import BaseModel, Field


class EdgeCreate(BaseModel):
    """Register an edge deployment (an off-platform enforcement point)."""

    name: str = Field(min_length=1, max_length=255)
    chain_uid: str = Field(min_length=1, max_length=255)
    verify_key_pem: str = Field(
        min_length=1, description="ECDSA P-256 public key (PEM) the edge signs records with"
    )
    authority_uid: str | None = Field(default=None, max_length=255)
    key_id: str | None = Field(
        default=None,
        max_length=255,
        description="JWKS kid the edge stamps at unmapped.signature_key_id; enforced when set",
    )


class EdgeResponse(BaseModel):
    id: uuid.UUID
    name: str
    chain_uid: str
    authority_uid: str | None
    key_id: str | None
    ingest_key_prefix: str
    status: str
    created_at: datetime.datetime
    last_ingest_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class EdgeCreatedResponse(EdgeResponse):
    """Registration response — carries the show-once ingest key."""

    ingest_key: str


class EdgeListResponse(BaseModel):
    edges: list[EdgeResponse]


class EdgeStreamSegment(BaseModel):
    """One (epoch, stream_id) run of verified records.

    This is the unit density is defined over: the emitter guarantees
    stream_seq dense within a segment and says nothing across segments —
    a new epoch on the same stream is a producer restart, a boundary
    rather than a loss. ``dense`` is therefore per-segment; two dense
    segments with a seq reset between them is a healthy stream that
    survived a crash.
    """

    stream_id: str
    # Producer boot time (Unix nanos). None for rows ingested before the
    # epoch column existed or from epoch-less producers.
    epoch: int | None
    first_seq: int
    last_seq: int
    records: int
    dense: bool
    # Verified rows in this segment carrying continuity anomalies
    # (a within-epoch gap, a chain re-anchor, an epoch regression).
    anomaly_records: int
    last_received_at: datetime.datetime


class EdgeStreamsResponse(BaseModel):
    """Evidence-continuity surface for one edge deployment."""

    edge_id: uuid.UUID
    name: str
    chain_uid: str
    status: str
    last_ingest_at: datetime.datetime | None
    verified: int
    quarantined: int
    segments: list[EdgeStreamSegment]


class IngestRecordResult(BaseModel):
    """Per-record outcome, in batch order."""

    uid: str | None = None
    dedupe_key: str | None = None
    status: str  # verified | quarantined | duplicate | error
    # Integrity failures — set only on quarantined records
    reason: str | None = None
    # Continuity observations — set only on verified records (gap, re-anchor)
    anomalies: str | None = None
    chain_position: int | None = None


class IngestResponse(BaseModel):
    results: list[IngestRecordResult]
    received: int
    verified: int
    quarantined: int
    duplicates: int
    errors: int
    anomalies: int
