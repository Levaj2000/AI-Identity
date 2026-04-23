"""Compliance export job — FSM transitions.

Four states (matches ``ExportStatus`` in the Pydantic schema):

    queued → building → ready
                   ↓
                failed

Invalid transitions raise ``InvalidJobTransitionError`` — the builder
catches and converts to a failed state so the row never ends up in an
inconsistent state even on unexpected exceptions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime

    from sqlalchemy.orm import Session

    from common.models import ComplianceExport
    from common.schemas.forensic_attestation import DSSEEnvelope

QUEUED = "queued"
BUILDING = "building"
READY = "ready"
FAILED = "failed"

_VALID_TRANSITIONS: dict[str, set[str]] = {
    QUEUED: {BUILDING, FAILED},
    BUILDING: {READY, FAILED},
    READY: set(),
    FAILED: set(),
}


class InvalidJobTransitionError(RuntimeError):
    """Raised when a transition is attempted from a non-source state."""


def _assert_transition(job: ComplianceExport, target: str) -> None:
    current = job.status
    if target not in _VALID_TRANSITIONS.get(current, set()):
        msg = f"invalid export job transition: {current!r} → {target!r} (job id={job.id})"
        raise InvalidJobTransitionError(msg)


def transition_to_building(
    db: Session,
    job: ComplianceExport,
    *,
    progress_pct: int | None = 0,
) -> None:
    """queued → building."""
    _assert_transition(job, BUILDING)
    job.status = BUILDING
    job.progress_pct = progress_pct
    db.flush()


def transition_to_ready(
    db: Session,
    job: ComplianceExport,
    *,
    archive_storage_path: str,
    archive_url: str | None,
    archive_url_expires_at: datetime.datetime | None,
    archive_sha256: str,
    archive_bytes: int,
    manifest_envelope: DSSEEnvelope,
    completed_at: datetime.datetime,
) -> None:
    """building → ready. Populates every downstream-visible column."""
    _assert_transition(job, READY)
    job.status = READY
    job.progress_pct = 100
    job.archive_storage_path = archive_storage_path
    job.archive_url = archive_url
    job.archive_url_expires_at = archive_url_expires_at
    job.archive_sha256 = archive_sha256
    job.archive_bytes = archive_bytes
    job.manifest_envelope = manifest_envelope.model_dump(mode="json")
    job.completed_at = completed_at
    job.error_code = None
    job.error_message = None
    db.flush()


def transition_to_failed(
    db: Session,
    job: ComplianceExport,
    *,
    error_code: str,
    error_message: str,
    completed_at: datetime.datetime,
) -> None:
    """queued|building → failed."""
    _assert_transition(job, FAILED)
    job.status = FAILED
    job.error_code = error_code
    job.error_message = error_message
    job.completed_at = completed_at
    db.flush()
