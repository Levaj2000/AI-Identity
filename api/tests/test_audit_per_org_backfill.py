"""Tests for the per-org chain backfill + verify scripts (Phase 2)."""

import uuid

from common.audit import create_audit_entry
from common.audit.writer import GENESIS
from common.config.settings import settings
from common.models import Agent, Organization, User
from scripts.backfill_per_org_chain import backfill_org
from scripts.verify_per_org_chain import verify_org

ORG_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ORG_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _seed_org(db_session, *, org_id: uuid.UUID, email_prefix: str) -> Agent:
    owner = User(
        id=uuid.uuid4(),
        email=f"{email_prefix}-owner@test",
        role="owner",
        tier="enterprise",
    )
    db_session.add(owner)
    db_session.flush()
    org = Organization(id=org_id, name=f"Org {email_prefix}", owner_id=owner.id, tier="business")
    db_session.add(org)
    db_session.flush()
    owner.org_id = org_id
    agent = Agent(
        id=uuid.uuid4(),
        user_id=owner.id,
        org_id=org_id,
        name=f"Agent {email_prefix}",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db_session.add(agent)
    db_session.commit()
    return agent


def _write_n_entries(db_session, agent, n: int) -> None:
    for _ in range(n):
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )


class TestBackfillOrg:
    def test_legacy_rows_only(self, db_session, monkeypatch):
        """A pure-legacy org: all rows have NULL chain. Backfill fills them in order."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
        _write_n_entries(db_session, agent, 5)

        processed, changed = backfill_org(db_session, ORG_A)
        assert processed == 5
        assert changed == 5

        result = verify_org(db_session, ORG_A)
        assert result.valid is True
        assert result.rows == 5

    def test_rewrites_dual_written_seq_after_legacy(self, db_session, monkeypatch):
        """Legacy rows + dual-written rows: backfill renumbers everything 1..N.

        The dual-written rows started at seq=1,2 because legacy NULLs are
        invisible to _get_last_org_chain_state. After backfill, the legacy
        rows should occupy seq 1..3 (chronologically earlier) and the
        dual-written rows should be renumbered to seq 4..5 with fresh
        entry_hash_org values.
        """
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        # 3 legacy rows (flag off, NULL chain columns)
        monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
        _write_n_entries(db_session, agent, 3)

        # 2 dual-written rows (flag on, will start at seq=1,2)
        monkeypatch.setattr(settings, "audit_dual_write_enabled", True)
        _write_n_entries(db_session, agent, 2)

        # Pre-backfill snapshot: dual-written rows have seq 1,2; legacy NULL.
        from common.models.audit_log import AuditLog

        before = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A)
            .order_by(AuditLog.id.asc())
            .all()
        )
        assert [r.org_chain_seq for r in before] == [None, None, None, 1, 2]
        original_dual_hashes = [before[3].entry_hash_org, before[4].entry_hash_org]

        # Backfill
        processed, changed = backfill_org(db_session, ORG_A)
        assert processed == 5
        assert changed == 5  # every row changed (legacy got values; dual-written got new seq)

        # Post-backfill: 1..5 in id order, fresh hashes on rows 4 and 5
        db_session.expire_all()
        after = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A)
            .order_by(AuditLog.id.asc())
            .all()
        )
        assert [r.org_chain_seq for r in after] == [1, 2, 3, 4, 5]
        assert after[0].prev_hash_org == GENESIS
        # Dual-written rows got new entry_hash_org values (seq changed → hash changed)
        assert after[3].entry_hash_org != original_dual_hashes[0]
        assert after[4].entry_hash_org != original_dual_hashes[1]

        result = verify_org(db_session, ORG_A)
        assert result.valid is True

    def test_idempotent_rerun_no_changes(self, db_session):
        """Backfill twice — second run reports zero changes."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 4)

        backfill_org(db_session, ORG_A)
        processed, changed = backfill_org(db_session, ORG_A)
        assert processed == 4
        assert changed == 0

    def test_dry_run_does_not_persist(self, db_session, monkeypatch):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
        _write_n_entries(db_session, agent, 3)

        processed, changed = backfill_org(db_session, ORG_A, dry_run=True)
        assert processed == 3
        assert changed == 3  # would-have-changed count

        # State unchanged
        from common.models.audit_log import AuditLog

        rows = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A)
            .order_by(AuditLog.id.asc())
            .all()
        )
        assert all(r.org_chain_seq is None for r in rows)

    def test_cross_org_isolation(self, db_session, monkeypatch):
        """Backfilling org A leaves org B untouched."""
        agent_a = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        agent_b = _seed_org(db_session, org_id=ORG_B, email_prefix="b")
        monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
        _write_n_entries(db_session, agent_a, 3)
        _write_n_entries(db_session, agent_b, 2)

        backfill_org(db_session, ORG_A)

        from common.models.audit_log import AuditLog

        b_rows = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_B)
            .order_by(AuditLog.id.asc())
            .all()
        )
        # Org B still has NULLs — backfill didn't touch it
        assert all(r.org_chain_seq is None for r in b_rows)
        # And org B still verifies as invalid (NULLs)
        assert verify_org(db_session, ORG_B).valid is False


class TestVerifyOrg:
    def test_detects_missing_seq(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 3)
        backfill_org(db_session, ORG_A)

        # Corrupt: delete a middle row to create a sequence gap
        from common.models.audit_log import AuditLog

        # The audit_log_no_update trigger only blocks UPDATE on PG, not
        # DELETE — and tests run on SQLite which doesn't have the trigger.
        # Simulate deletion via direct SQL bypass.
        middle = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A, AuditLog.org_chain_seq == 2)
            .one()
        )
        db_session.delete(middle)
        db_session.commit()

        result = verify_org(db_session, ORG_A)
        assert result.valid is False
        assert "seq gap" in (result.reason or "")

    def test_detects_tampered_hash(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 2)
        backfill_org(db_session, ORG_A)

        # Tamper: change the endpoint on a row, leave hash stale
        from common.models.audit_log import AuditLog

        row = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A, AuditLog.org_chain_seq == 2)
            .one()
        )
        row.endpoint = "/tampered"
        db_session.commit()

        result = verify_org(db_session, ORG_A)
        assert result.valid is False
        assert "entry_hash_org recompute mismatch" in (result.reason or "")
