"""Unit tests for the compliance-export orphan reaper."""

from __future__ import annotations

import datetime
import uuid

import pytest

from common.compliance.orphan_cleanup import (
    DEFAULT_STALE_THRESHOLD_MINUTES,
    reap_orphaned_exports,
)
from common.models import ComplianceExport, Organization, User


@pytest.fixture
def org(db_session):
    owner = User(
        id=uuid.UUID("00000000-0000-0000-0000-00000000bbb1"),
        email="orphan-owner@example.test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(owner)
    db_session.flush()
    organisation = Organization(
        id=uuid.UUID("00000000-0000-0000-0000-00000000bbbb"),
        name="Orphan Test Org",
        owner_id=owner.id,
        tier="business",
    )
    db_session.add(organisation)
    db_session.commit()
    return {"owner": owner, "org": organisation}


def _insert(
    db_session,
    org_bundle,
    *,
    status: str,
    created_at: datetime.datetime,
) -> ComplianceExport:
    job = ComplianceExport(
        id=uuid.uuid4(),
        org_id=org_bundle["org"].id,
        requested_by=org_bundle["owner"].id,
        profile="soc2_tsc_2017",
        audit_period_start=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        audit_period_end=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC),
        agent_ids=None,
        agent_ids_hash="",
        status=status,
        created_at=created_at,
    )
    db_session.add(job)
    db_session.commit()
    return job


class TestReapOrphans:
    def test_old_queued_is_reaped(self, db_session, org):
        now = datetime.datetime.now(tz=datetime.UTC)
        stale = now - datetime.timedelta(minutes=DEFAULT_STALE_THRESHOLD_MINUTES + 5)
        job = _insert(db_session, org, status="queued", created_at=stale)

        reaped = reap_orphaned_exports(db_session, now=now)
        assert reaped == 1

        db_session.refresh(job)
        assert job.status == "failed"
        assert job.error_code == "orphaned_on_restart"
        assert "queued" in (job.error_message or "")
        assert job.completed_at is not None

    def test_old_building_is_reaped(self, db_session, org):
        now = datetime.datetime.now(tz=datetime.UTC)
        stale = now - datetime.timedelta(minutes=DEFAULT_STALE_THRESHOLD_MINUTES + 5)
        job = _insert(db_session, org, status="building", created_at=stale)

        reaped = reap_orphaned_exports(db_session, now=now)
        assert reaped == 1

        db_session.refresh(job)
        assert job.status == "failed"
        # Error message references the ORIGINAL state, not the post-reap 'failed'
        assert "building" in (job.error_message or "")

    def test_fresh_inflight_job_is_not_reaped(self, db_session, org):
        now = datetime.datetime.now(tz=datetime.UTC)
        fresh = now - datetime.timedelta(minutes=1)
        job = _insert(db_session, org, status="building", created_at=fresh)

        reaped = reap_orphaned_exports(db_session, now=now)
        assert reaped == 0

        db_session.refresh(job)
        assert job.status == "building"  # untouched

    def test_terminal_jobs_are_never_reaped(self, db_session, org):
        now = datetime.datetime.now(tz=datetime.UTC)
        stale = now - datetime.timedelta(hours=12)
        ready_job = _insert(db_session, org, status="ready", created_at=stale)
        failed_job = _insert(db_session, org, status="failed", created_at=stale)

        reaped = reap_orphaned_exports(db_session, now=now)
        assert reaped == 0

        db_session.refresh(ready_job)
        db_session.refresh(failed_job)
        assert ready_job.status == "ready"
        assert failed_job.status == "failed"

    def test_custom_threshold_overrides_default(self, db_session, org):
        now = datetime.datetime.now(tz=datetime.UTC)
        # 7 minutes old — below default (10) but above 5.
        job = _insert(
            db_session,
            org,
            status="building",
            created_at=now - datetime.timedelta(minutes=7),
        )

        # At default threshold (10 min), NOT reaped.
        assert reap_orphaned_exports(db_session, now=now) == 0
        db_session.refresh(job)
        assert job.status == "building"

        # At 5 min threshold, IS reaped.
        assert reap_orphaned_exports(db_session, stale_threshold_minutes=5, now=now) == 1
        db_session.refresh(job)
        assert job.status == "failed"

    def test_reap_is_idempotent(self, db_session, org):
        """Running twice on the same orphan set reaps once."""
        now = datetime.datetime.now(tz=datetime.UTC)
        stale = now - datetime.timedelta(hours=1)
        _insert(db_session, org, status="queued", created_at=stale)

        first = reap_orphaned_exports(db_session, now=now)
        second = reap_orphaned_exports(db_session, now=now)
        assert first == 1
        assert second == 0  # already transitioned to failed, not matched anymore
