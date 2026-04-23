"""Unit tests for the export job FSM + agent_ids_hash helper."""

from __future__ import annotations

import datetime
import uuid

import pytest

from common.compliance.agent_ids_hash import agent_ids_hash
from common.compliance.job import (
    BUILDING,
    FAILED,
    QUEUED,
    READY,
    InvalidJobTransitionError,
    transition_to_building,
    transition_to_failed,
    transition_to_ready,
)
from common.models import ComplianceExport
from common.schemas.forensic_attestation import DSSEEnvelope, DSSESignature


def _utc_now() -> datetime.datetime:
    return datetime.datetime(2026, 4, 23, tzinfo=datetime.UTC)


def _make_job(status: str = QUEUED) -> ComplianceExport:
    """Detached job row for FSM tests — no DB writes."""
    return ComplianceExport(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        requested_by=uuid.uuid4(),
        profile="soc2_tsc_2017",
        audit_period_start=_utc_now(),
        audit_period_end=_utc_now() + datetime.timedelta(days=30),
        agent_ids=None,
        agent_ids_hash="",
        status=status,
    )


def _fake_envelope() -> DSSEEnvelope:
    return DSSEEnvelope(
        payloadType="application/vnd.ai-identity.export-manifest+json",
        payload="Zm9v",  # "foo"
        signatures=[DSSESignature(keyid="local:x", sig="YmFy")],  # "bar"
    )


class _StubSession:
    """Minimal session stand-in — the FSM only calls flush()."""

    def flush(self) -> None:
        pass


# ── Happy transitions ────────────────────────────────────────────────


class TestHappyPath:
    def test_queued_to_building(self):
        job = _make_job(QUEUED)
        transition_to_building(_StubSession(), job)
        assert job.status == BUILDING
        assert job.progress_pct == 0

    def test_building_to_ready_populates_everything(self):
        job = _make_job(BUILDING)
        transition_to_ready(
            _StubSession(),
            job,
            archive_storage_path="/tmp/x.zip",
            archive_url=None,
            archive_url_expires_at=None,
            archive_sha256="a" * 64,
            archive_bytes=1234,
            manifest_envelope=_fake_envelope(),
            completed_at=_utc_now(),
        )
        assert job.status == READY
        assert job.progress_pct == 100
        assert job.archive_storage_path == "/tmp/x.zip"
        assert job.archive_sha256 == "a" * 64
        assert job.archive_bytes == 1234
        assert job.manifest_envelope is not None
        assert job.completed_at == _utc_now()

    def test_queued_to_failed(self):
        job = _make_job(QUEUED)
        transition_to_failed(
            _StubSession(),
            job,
            error_code="signer_misconfigured",
            error_message="no key",
            completed_at=_utc_now(),
        )
        assert job.status == FAILED
        assert job.error_code == "signer_misconfigured"
        assert job.completed_at == _utc_now()

    def test_building_to_failed(self):
        job = _make_job(BUILDING)
        transition_to_failed(
            _StubSession(),
            job,
            error_code="build_failed",
            error_message="boom",
            completed_at=_utc_now(),
        )
        assert job.status == FAILED


# ── Invalid transitions ──────────────────────────────────────────────


class TestInvalidTransitions:
    def test_ready_is_terminal(self):
        job = _make_job(READY)
        with pytest.raises(InvalidJobTransitionError):
            transition_to_building(_StubSession(), job)
        with pytest.raises(InvalidJobTransitionError):
            transition_to_failed(
                _StubSession(),
                job,
                error_code="x",
                error_message="y",
                completed_at=_utc_now(),
            )

    def test_failed_is_terminal(self):
        job = _make_job(FAILED)
        with pytest.raises(InvalidJobTransitionError):
            transition_to_building(_StubSession(), job)
        with pytest.raises(InvalidJobTransitionError):
            transition_to_ready(
                _StubSession(),
                job,
                archive_storage_path="x",
                archive_url=None,
                archive_url_expires_at=None,
                archive_sha256="a" * 64,
                archive_bytes=1,
                manifest_envelope=_fake_envelope(),
                completed_at=_utc_now(),
            )

    def test_queued_cannot_skip_to_ready(self):
        job = _make_job(QUEUED)
        with pytest.raises(InvalidJobTransitionError):
            transition_to_ready(
                _StubSession(),
                job,
                archive_storage_path="x",
                archive_url=None,
                archive_url_expires_at=None,
                archive_sha256="a" * 64,
                archive_bytes=1,
                manifest_envelope=_fake_envelope(),
                completed_at=_utc_now(),
            )


# ── agent_ids_hash ───────────────────────────────────────────────────


class TestAgentIdsHash:
    def test_null_is_empty_string(self):
        assert agent_ids_hash(None) == ""
        assert agent_ids_hash([]) == ""

    def test_order_independent(self):
        a = uuid.UUID("11111111-1111-1111-1111-111111111111")
        b = uuid.UUID("22222222-2222-2222-2222-222222222222")
        assert agent_ids_hash([a, b]) == agent_ids_hash([b, a])

    def test_different_sets_differ(self):
        a = uuid.UUID("11111111-1111-1111-1111-111111111111")
        b = uuid.UUID("22222222-2222-2222-2222-222222222222")
        c = uuid.UUID("33333333-3333-3333-3333-333333333333")
        assert agent_ids_hash([a, b]) != agent_ids_hash([a, c])

    def test_single_id_differs_from_null(self):
        a = uuid.UUID("11111111-1111-1111-1111-111111111111")
        assert agent_ids_hash([a]) != ""
        assert len(agent_ids_hash([a])) == 64
