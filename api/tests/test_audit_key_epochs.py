"""Tests for key-epoch tracking on the audit chain.

An org's forensic_verify_key is minted lazily and can be regenerated, so
one org's chain can span several HMAC key epochs. These tests cover:

  - Every row is stamped with the fingerprint of the key that hashed it
  - verify_chain crosses a key-mint boundary (global → org key) cleanly,
    reporting the pre-key rows as legacy_key_entries instead of a break
  - verify_chain crosses a key regeneration when the retired key is kept
    in forensic_key_history — and breaks (honestly) when it is not
  - Tampering is still detected across epochs
  - The forensic-verify-key endpoints expose fingerprints, retain retired
    keys on regeneration, and warn when a fresh key can't cover history
  - scripts/backfill_key_fingerprints.py stamps legacy NULL rows with the
    right epoch and leaves unmatched rows NULL
"""

import uuid
from datetime import UTC, datetime

from common.audit import create_audit_entry, verify_chain
from common.audit.writer import key_fingerprint
from common.config.settings import settings
from common.models import Agent, Organization, User
from common.models.audit_log import AuditLog
from common.models.org_membership import OrgMembership, OrgRole
from scripts.backfill_key_fingerprints import backfill_org

ORG_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

KEY_A = "org-key-epoch-a"
KEY_B = "org-key-epoch-b"


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


def _set_org_key(db_session, org_id: uuid.UUID, key: str | None, history: list | None = None):
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    org.forensic_verify_key = key
    if history is not None:
        org.forensic_key_history = history
    db_session.commit()


class TestKeyFingerprintStamping:
    def test_stamps_global_key_fingerprint_when_org_has_no_key(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 1)

        row = db_session.query(AuditLog).filter(AuditLog.org_id == ORG_A).one()
        assert row.key_fingerprint == key_fingerprint(settings.audit_hmac_key)

    def test_stamps_org_key_fingerprint(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _set_org_key(db_session, ORG_A, KEY_A)
        _write_n_entries(db_session, agent, 1)

        row = db_session.query(AuditLog).filter(AuditLog.org_id == ORG_A).one()
        assert row.key_fingerprint == key_fingerprint(KEY_A)
        assert row.key_fingerprint != key_fingerprint(settings.audit_hmac_key)


class TestVerifyChainAcrossEpochs:
    def test_chain_spanning_key_mint_verifies(self, db_session):
        """Rows written before the org key existed (global epoch) + rows
        after the mint verify as one intact chain, with the pre-key rows
        counted as legacy — the exact scenario that used to read as
        CHAIN BROKEN."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 3)  # global-key epoch
        _set_org_key(db_session, ORG_A, KEY_A)  # lazy mint
        _write_n_entries(db_session, agent, 2)  # org-key epoch

        result = verify_chain(db_session, org_id=ORG_A)
        assert result.valid is True
        assert result.entries_verified == 5
        assert result.legacy_key_entries == 3
        assert "earlier key epoch" in result.message

    def test_chain_spanning_regeneration_verifies_with_history(self, db_session):
        """Regeneration retains the old key in forensic_key_history, so the
        old epoch's rows still verify."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _set_org_key(db_session, ORG_A, KEY_A)
        _write_n_entries(db_session, agent, 3)  # epoch A

        retired = {
            "key": KEY_A,
            "key_fingerprint": key_fingerprint(KEY_A),
            "retired_at": datetime.now(UTC).isoformat(),
        }
        _set_org_key(db_session, ORG_A, KEY_B, history=[retired])
        _write_n_entries(db_session, agent, 2)  # epoch B

        result = verify_chain(db_session, org_id=ORG_A)
        assert result.valid is True
        assert result.entries_verified == 5
        assert result.legacy_key_entries == 3

    def test_regeneration_without_history_breaks_with_epoch_note(self, db_session):
        """Discarding the old key (pre-fix behavior) makes its epoch
        unverifiable — the failure message must name the missing epoch so
        it isn't mistaken for tampering."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _set_org_key(db_session, ORG_A, KEY_A)
        _write_n_entries(db_session, agent, 2)
        _set_org_key(db_session, ORG_A, KEY_B)  # old key discarded

        result = verify_chain(db_session, org_id=ORG_A)
        assert result.valid is False
        assert "key epoch" in result.message
        assert key_fingerprint(KEY_A) in result.message

    def test_tamper_still_detected_across_epochs(self, db_session):
        """Epoch awareness must not weaken tamper detection: a modified row
        in a held epoch still breaks the chain."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 2)  # global epoch
        _set_org_key(db_session, ORG_A, KEY_A)
        _write_n_entries(db_session, agent, 2)  # epoch A

        victim = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A)
            .order_by(AuditLog.org_chain_seq.desc())
            .first()
        )
        victim.endpoint = "/tampered"
        db_session.commit()

        result = verify_chain(db_session, org_id=ORG_A)
        assert result.valid is False
        assert result.first_broken_id == victim.id


class TestForensicKeyEndpoints:
    def _grant_membership(self, db_session, test_user):
        db_session.add(
            OrgMembership(
                id=uuid.uuid4(),
                org_id=test_user.org_id,
                user_id=test_user.id,
                role=OrgRole.owner.value,
            )
        )
        db_session.commit()

    def test_lazy_mint_returns_fingerprint_and_epoch_warning(
        self, client, db_session, test_user, auth_headers
    ):
        self._grant_membership(db_session, test_user)

        resp = client.get("/api/v1/orgs/me/forensic-verify-key", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["key_fingerprint"] == key_fingerprint(body["forensic_verify_key"])
        assert body["retired_keys"] == []
        assert "earlier key epoch" in body["warning"]

        # Second fetch: key already exists — no just-minted warning
        resp = client.get("/api/v1/orgs/me/forensic-verify-key", headers=auth_headers)
        assert "warning" not in resp.json()

    def test_regenerate_retains_retired_key(self, client, db_session, test_user, auth_headers):
        self._grant_membership(db_session, test_user)

        first = client.get("/api/v1/orgs/me/forensic-verify-key", headers=auth_headers).json()
        old_key = first["forensic_verify_key"]

        regen = client.post("/api/v1/orgs/me/forensic-verify-key/regenerate", headers=auth_headers)
        assert regen.status_code == 200
        body = regen.json()
        assert body["forensic_verify_key"] != old_key
        assert body["retired_key_fingerprint"] == key_fingerprint(old_key)
        assert "--key" in body["warning"]

        # The retired key is retrievable — old exports stay verifiable
        current = client.get("/api/v1/orgs/me/forensic-verify-key", headers=auth_headers).json()
        assert [k["key"] for k in current["retired_keys"]] == [old_key]
        assert current["retired_keys"][0]["key_fingerprint"] == key_fingerprint(old_key)

    def test_chain_survives_regeneration_end_to_end(
        self, client, db_session, test_user, auth_headers
    ):
        """Write → regenerate → write → verify: the chain stays valid because
        the retired key is retained."""
        self._grant_membership(db_session, test_user)
        agent = Agent(
            id=uuid.uuid4(),
            user_id=test_user.id,
            org_id=test_user.org_id,
            name="epoch-agent",
            status="active",
            capabilities=[],
            metadata_={},
        )
        db_session.add(agent)
        db_session.commit()

        client.get("/api/v1/orgs/me/forensic-verify-key", headers=auth_headers)  # mint
        _write_n_entries(db_session, agent, 2)
        client.post("/api/v1/orgs/me/forensic-verify-key/regenerate", headers=auth_headers)
        _write_n_entries(db_session, agent, 2)

        result = verify_chain(db_session, org_id=test_user.org_id)
        assert result.valid is True
        assert result.entries_verified == 4
        assert result.legacy_key_entries == 2


class TestBackfillKeyFingerprints:
    def _null_fingerprints(self, db_session, org_id):
        for row in db_session.query(AuditLog).filter(AuditLog.org_id == org_id).all():
            row.key_fingerprint = None
        db_session.commit()

    def test_stamps_legacy_rows_with_correct_epochs(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 2)  # global epoch
        _set_org_key(db_session, ORG_A, KEY_A)
        _write_n_entries(db_session, agent, 3)  # epoch A
        self._null_fingerprints(db_session, ORG_A)  # simulate pre-feature rows

        processed, stamped, unmatched = backfill_org(db_session, ORG_A)
        assert (processed, stamped, unmatched) == (5, 5, 0)

        fps = [
            r.key_fingerprint
            for r in db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A)
            .order_by(AuditLog.org_chain_seq.asc())
            .all()
        ]
        global_fp = key_fingerprint(settings.audit_hmac_key)
        assert fps == [global_fp, global_fp] + [key_fingerprint(KEY_A)] * 3

    def test_dry_run_writes_nothing(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 2)
        self._null_fingerprints(db_session, ORG_A)

        processed, stamped, unmatched = backfill_org(db_session, ORG_A, dry_run=True)
        assert (processed, stamped, unmatched) == (2, 2, 0)
        remaining = (
            db_session.query(AuditLog)
            .filter(AuditLog.org_id == ORG_A, AuditLog.key_fingerprint.is_(None))
            .count()
        )
        assert remaining == 2

    def test_unmatched_rows_left_null(self, db_session):
        """Rows hashed under a key the server no longer holds stay NULL —
        surfaced for investigation, never guessed."""
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _set_org_key(db_session, ORG_A, KEY_A)
        _write_n_entries(db_session, agent, 2)
        self._null_fingerprints(db_session, ORG_A)
        _set_org_key(db_session, ORG_A, KEY_B)  # KEY_A discarded, no history

        processed, stamped, unmatched = backfill_org(db_session, ORG_A)
        assert (processed, stamped, unmatched) == (2, 0, 2)

    def test_idempotent_skips_stamped_rows(self, db_session):
        agent = _seed_org(db_session, org_id=ORG_A, email_prefix="a")
        _write_n_entries(db_session, agent, 3)  # stamped at write time

        processed, stamped, unmatched = backfill_org(db_session, ORG_A)
        assert (processed, stamped, unmatched) == (0, 0, 0)
