"""Tests for the per-org audit chain (Phase 1 dual-write).

Covers:
  - First write in an org sets prev_hash_org=GENESIS, org_chain_seq=1
  - Sequential writes in the same org chain correctly (1..N, monotonic)
  - Two orgs maintain independent chains (no shared sequence)
  - Interleaved cross-org writes preserve each org's chain
  - prev_hash_org/entry_hash_org pair recomputes correctly per row
  - audit_dual_write_enabled=False leaves new columns NULL
  - The global chain (prev_hash/entry_hash) is unaffected by dual-write
  - The (org_id, org_chain_seq) UNIQUE constraint catches duplicates
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from common.audit import (
    compute_entry_hash_org,
    create_audit_entry,
    verify_chain,
    verify_global_chain,
)
from common.audit.writer import GENESIS, _ensure_utc
from common.config.settings import settings
from common.models import Agent, Organization, User
from common.models.audit_log import AuditLog


def _seed_org(db_session, *, org_id: uuid.UUID, email_prefix: str) -> Agent:
    """Create an org + owner + one agent. Returns the agent."""
    owner = User(
        id=uuid.uuid4(), email=f"{email_prefix}-owner@test", role="owner", tier="enterprise"
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


ORG_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ORG_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class TestSingleOrgChain:
    def test_first_write_starts_with_genesis(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        assert entry.prev_hash_org == GENESIS
        assert entry.org_chain_seq == 1
        assert entry.entry_hash_org is not None
        assert len(entry.entry_hash_org) == 64  # hex sha256

    def test_sequence_is_monotonic_within_org(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        entries = [
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint="/v1/chat",
                method="POST",
                decision="allow",
                request_metadata={"seq": i},
            )
            for i in range(5)
        ]

        assert [e.org_chain_seq for e in entries] == [1, 2, 3, 4, 5]

    def test_prev_hash_org_links_to_previous_entry(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        e1 = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        e2 = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        assert e2.prev_hash_org == e1.entry_hash_org

    def test_entry_hash_org_recomputes(self, db_session):
        """The stored entry_hash_org matches a fresh recomputation."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        org = db_session.query(Organization).filter(Organization.id == ORG_A).one()

        entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )

        # The writer uses the org's forensic_verify_key if present, else
        # the global key. _seed_org doesn't set one, so this org uses the
        # global key (hmac_key=None falls through to settings.audit_hmac_key).
        recomputed = compute_entry_hash_org(
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
            prev_hash_org=entry.prev_hash_org,
            hmac_key=org.forensic_verify_key,
        )
        assert recomputed == entry.entry_hash_org


class TestCrossOrgChainsIndependent:
    def test_each_org_has_own_genesis(self, db_session):
        agent_a = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        agent_b = _seed_org(db_session, org_id=ORG_B, email_prefix="b")

        e_a1 = create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        e_b1 = create_audit_entry(
            db_session,
            agent_id=agent_b.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )

        assert e_a1.prev_hash_org == GENESIS
        assert e_b1.prev_hash_org == GENESIS
        assert e_a1.org_chain_seq == 1
        assert e_b1.org_chain_seq == 1

    def test_interleaved_writes_preserve_per_org_sequence(self, db_session):
        agent_a = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        agent_b = _seed_org(db_session, org_id=ORG_B, email_prefix="b")

        # Interleave: A, B, A, B, A — A should be 1,2,3; B should be 1,2
        a1 = create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        b1 = create_audit_entry(
            db_session,
            agent_id=agent_b.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        a2 = create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        b2 = create_audit_entry(
            db_session,
            agent_id=agent_b.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        a3 = create_audit_entry(
            db_session,
            agent_id=agent_a.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )

        assert [a1.org_chain_seq, a2.org_chain_seq, a3.org_chain_seq] == [1, 2, 3]
        assert [b1.org_chain_seq, b2.org_chain_seq] == [1, 2]
        # A's chain links A→A, not A→B
        assert a2.prev_hash_org == a1.entry_hash_org
        assert a3.prev_hash_org == a2.entry_hash_org
        assert b2.prev_hash_org == b1.entry_hash_org


class TestFeatureFlag:
    def test_flag_off_leaves_columns_null(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        entry = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )

        assert entry.prev_hash_org is None
        assert entry.entry_hash_org is None
        assert entry.org_chain_seq is None

    def test_flag_off_then_on_resumes_at_seq_1(self, db_session, monkeypatch):
        """Mid-deploy flip: an org's first dual-write row starts at seq=1.

        Mirrors the Phase 2 backfill story — legacy NULL rows are invisible
        to _get_last_org_chain_state, so the first populated row in an org
        starts the chain fresh. Backfill will rewrite history; the writer
        doesn't need to coordinate with it.
        """
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        # Two writes with the flag off — both rows have NULL chain columns.
        monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )

        # Flip the flag on. The next row starts the org's chain.
        monkeypatch.setattr(settings, "audit_dual_write_enabled", True)
        first_populated = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )

        assert first_populated.prev_hash_org == GENESIS
        assert first_populated.org_chain_seq == 1


class TestGlobalChainUnaffected:
    def test_global_chain_still_verifies_with_dual_write(self, db_session):
        """Adding per-org chain columns doesn't break the existing global chain."""
        agent_a = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        agent_b = _seed_org(db_session, org_id=ORG_B, email_prefix="b")

        for agent in (agent_a, agent_b, agent_a, agent_b):
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint="/x",
                method="GET",
                decision="allow",
                request_metadata={},
            )

        # Global chain spans both orgs, per-org chains stay isolated
        result = verify_global_chain(db_session)
        assert result.valid is True
        assert result.entries_verified == 4
        assert verify_chain(db_session, org_id=ORG_A).entries_verified == 2
        assert verify_chain(db_session, org_id=ORG_B).entries_verified == 2


class TestSequenceUniqueness:
    def test_duplicate_org_chain_seq_rejected(self, db_session):
        """The partial UNIQUE index is the belt-and-suspenders guard.

        If the advisory lock ever fails, a duplicate (org_id, seq) must
        still fail at the DB level rather than silently corrupt the chain.
        """
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")

        e1 = create_audit_entry(
            db_session,
            agent_id=agent.id,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
        )
        # Hand-craft a duplicate row at the same seq
        duplicate = AuditLog(
            agent_id=agent.id,
            user_id=agent.user_id,
            org_id=ORG_A,
            endpoint="/x",
            method="GET",
            decision="allow",
            request_metadata={},
            created_at=e1.created_at,
            entry_hash="x" * 64,
            prev_hash="y" * 64,
            prev_hash_org=GENESIS,
            entry_hash_org="z" * 64,
            org_chain_seq=e1.org_chain_seq,  # same seq → must fail
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestBatchedChainWalk:
    """verify_chain pages by seeking on org_chain_seq, not OFFSET.

    Every other test in this file seeds fewer rows than the default
    batch_size, so the paging loop runs exactly once and never exercises
    the cursor. These force multiple batches with a small batch_size.
    """

    def _write(self, db_session, agent, n):
        return [
            create_audit_entry(
                db_session,
                agent_id=agent.id,
                endpoint=f"/x/{i}",
                method="GET",
                decision="allow",
                request_metadata={},
            )
            for i in range(n)
        ]

    def test_org_chain_verifies_across_batches(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        self._write(db_session, agent, 7)

        result = verify_chain(db_session, org_id=ORG_A, batch_size=2)

        assert result.valid is True
        assert result.total_entries == 7
        # Every row walked exactly once — a cursor that skipped or
        # re-read rows would land short or long here.
        assert result.entries_verified == 7

    def test_batched_walk_detects_tamper_in_later_batch(self, db_session):
        """The row that matters is past the first batch boundary.

        If the cursor skipped rows, a tampered entry in a later batch
        would verify clean — the chain would silently lie.
        """
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        entries = self._write(db_session, agent, 7)
        target = entries[5]  # batch 3 of 4 at batch_size=2

        db_session.execute(
            AuditLog.__table__.update()
            .where(AuditLog.id == target.id)
            .values(entry_hash_org="deadbeef" * 8)
        )
        db_session.commit()

        result = verify_chain(db_session, org_id=ORG_A, batch_size=2)

        assert result.valid is False
        assert result.first_broken_id == target.id

    def test_agent_filtered_walk_spans_sparse_seq(self, db_session):
        """An agent-filtered view has gaps in org_chain_seq by design.

        Two agents interleaved in one org means agent A's rows carry
        seq 1,3,5,7 — the cursor must seek on the real seq values, not
        assume they are contiguous.
        """
        agent_a = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        agent_b = Agent(
            id=uuid.uuid4(),
            user_id=agent_a.user_id,
            org_id=ORG_A,
            name="Agent A2",
            status="active",
            capabilities=[],
            metadata_={},
        )
        db_session.add(agent_b)
        db_session.commit()

        for _ in range(4):
            self._write(db_session, agent_a, 1)
            self._write(db_session, agent_b, 1)

        result = verify_chain(db_session, org_id=ORG_A, agent_id=agent_a.id, batch_size=2)

        assert result.valid is True
        assert result.entries_verified == 4
