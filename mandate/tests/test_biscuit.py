"""Tests for common/biscuit/ — mint, attenuate, authorize.

Pure-logic tests (no Mongo, no FastAPI): keys are generated per-module,
time is passed explicitly so nothing here depends on the wall clock.
"""

import datetime as dt

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from common.biscuit import (
    BiscuitUnavailableError,
    attenuate_spend_ceiling,
    authorize_presentation,
    mint_mandate_biscuit,
    root_public_key_hex,
)

AGENT_ID = "0b6ef1a2-9f14-4c1e-8f7a-2d5c3e9b1a70"
MANDATE_ID = "mnd_ab12cd34"
VALID_FROM = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
VALID_UNTIL = dt.datetime(2026, 12, 31, tzinfo=dt.UTC)
NOW = dt.datetime(2026, 8, 7, tzinfo=dt.UTC)


@pytest.fixture(scope="module")
def root_pem() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture(scope="module")
def minted(root_pem):
    return mint_mandate_biscuit(
        private_key_pem=root_pem,
        mandate_id=MANDATE_ID,
        subject_agent_id=AGENT_ID,
        subject_org_id="org_demo",
        scope=["spend:commerce", "read:catalog"],
        valid_from=VALID_FROM,
        valid_until=VALID_UNTIL,
        limit_cents=10_000,
        currency="USD",
    )


def _authorize(minted, **overrides):
    kwargs = dict(
        agent_id=AGENT_ID,
        amount_cents=3_000,
        scope="spend:commerce",
        currency="USD",
        now=NOW,
    )
    kwargs.update(overrides)
    token = overrides.pop("token", None) or minted.token
    kwargs.pop("token", None)
    return authorize_presentation(token, minted.root_public_key, **kwargs)


class TestMint:
    def test_no_key_configured_raises(self):
        with pytest.raises(BiscuitUnavailableError):
            mint_mandate_biscuit(
                private_key_pem="",
                mandate_id=MANDATE_ID,
                subject_agent_id=AGENT_ID,
                subject_org_id="org_demo",
                scope=["spend:commerce"],
                valid_from=VALID_FROM,
            )

    def test_mint_returns_token_and_key(self, minted, root_pem):
        assert minted.token
        assert minted.root_public_key == root_public_key_hex(root_pem)
        assert len(minted.revocation_ids) == 1  # authority block only

    def test_header_sized(self, minted):
        # Has to travel as an HTTP header value
        assert len(minted.token) < 4096


class TestAuthorize:
    def test_within_grant_allowed(self, minted):
        result = _authorize(minted)
        assert result.allowed
        assert result.mandate_id == MANDATE_ID
        assert result.block_count == 1

    def test_second_granted_scope_allowed(self, minted):
        assert _authorize(minted, scope="read:catalog").allowed

    def test_over_limit_denied(self, minted):
        result = _authorize(minted, amount_cents=40_500)
        assert not result.allowed
        assert result.mandate_id == MANDATE_ID  # extractable even on deny
        assert "check" in (result.deny_detail or "").lower()

    def test_wrong_subject_denied(self, minted):
        assert not _authorize(minted, agent_id="someone-else").allowed

    def test_ungranted_scope_denied(self, minted):
        assert not _authorize(minted, scope="admin:delete").allowed

    def test_wrong_currency_denied(self, minted):
        assert not _authorize(minted, currency="EUR").allowed

    def test_expired_denied(self, minted):
        after_expiry = dt.datetime(2027, 6, 1, tzinfo=dt.UTC)
        assert not _authorize(minted, now=after_expiry).allowed

    def test_before_valid_from_denied(self, minted):
        early = dt.datetime(2025, 6, 1, tzinfo=dt.UTC)
        assert not _authorize(minted, now=early).allowed

    def test_settlement_mode_passes_authority_ceiling(self, minted):
        # Money already moved: settlement must be RECORDABLE past the grant
        # so the breach can be evidenced. The verifier asserts settlement.
        result = _authorize(minted, amount_cents=40_500, settlement=True)
        assert result.allowed

    def test_settlement_mode_still_enforces_subject_and_scope(self, minted):
        assert not _authorize(minted, amount_cents=100, settlement=True, agent_id="x").allowed
        assert not _authorize(minted, amount_cents=100, settlement=True, scope="admin:x").allowed

    def test_no_spend_limit_means_no_amount_ceiling(self, root_pem):
        unlimited = mint_mandate_biscuit(
            private_key_pem=root_pem,
            mandate_id="mnd_nolimit1",
            subject_agent_id=AGENT_ID,
            subject_org_id="org_demo",
            scope=["spend:commerce"],
            valid_from=VALID_FROM,
        )
        result = authorize_presentation(
            unlimited.token,
            unlimited.root_public_key,
            agent_id=AGENT_ID,
            amount_cents=99_999_999,
            scope="spend:commerce",
            now=NOW,
        )
        assert result.allowed


class TestAttenuation:
    def test_narrowed_ceiling_allows_within(self, minted):
        narrowed = attenuate_spend_ceiling(
            minted.token, minted.root_public_key, ceiling_cents=2_000
        )
        result = _authorize(minted, token=narrowed, amount_cents=1_500)
        assert result.allowed
        assert result.block_count == 2
        assert len(result.revocation_ids) == 2

    def test_narrowed_ceiling_denies_over(self, minted):
        narrowed = attenuate_spend_ceiling(
            minted.token, minted.root_public_key, ceiling_cents=2_000
        )
        result = _authorize(minted, token=narrowed, amount_cents=4_000)
        assert not result.allowed
        # the ATTENUATION block (n°1) failed, not the authority ceiling
        assert "block n°1" in (result.deny_detail or "")

    def test_injected_facts_cannot_satisfy_checks(self, minted):
        # A malicious holder appends a block carrying its own facts named
        # like the verifier's (amount/subject/currency). Block-scoping must
        # keep them invisible to the authority checks — the same bug class
        # as informational-fact/check name collisions at mint time.
        from biscuit_auth import Algorithm, Biscuit, BlockBuilder, PublicKey

        token = Biscuit.from_base64(
            minted.token,
            PublicKey.from_bytes(bytes.fromhex(minted.root_public_key), Algorithm.Ed25519),
        )
        evil = BlockBuilder()
        evil.add_code(
            'amount(5); subject("0b6ef1a2-9f14-4c1e-8f7a-2d5c3e9b1a70"); currency("USD");'
        )
        injected = token.append(evil).to_base64()
        result = _authorize(minted, token=injected, amount_cents=40_500)
        assert not result.allowed

    def test_settlement_does_not_bypass_attenuation_ceiling(self, minted):
        # A sub-agent's delegated cap is absolute — settlement mode must not
        # let a narrowed token settle past its attenuation block.
        narrowed = attenuate_spend_ceiling(
            minted.token, minted.root_public_key, ceiling_cents=2_000
        )
        result = _authorize(minted, token=narrowed, amount_cents=4_000, settlement=True)
        assert not result.allowed
        assert "block n°1" in (result.deny_detail or "")

    def test_attenuation_cannot_widen(self, minted):
        # A "wider" ceiling appends a check that passes, but the authority
        # block's own 10_000 ceiling still applies — rights never grow.
        widened = attenuate_spend_ceiling(
            minted.token, minted.root_public_key, ceiling_cents=50_000
        )
        assert not _authorize(minted, token=widened, amount_cents=40_000).allowed


class TestTamper:
    def test_tampered_token_rejected(self, minted):
        raw = bytearray(minted.token.encode())
        raw[len(raw) // 2] ^= 0x01
        result = authorize_presentation(
            raw.decode(errors="ignore"),
            minted.root_public_key,
            agent_id=AGENT_ID,
            amount_cents=100,
            scope="spend:commerce",
            now=NOW,
        )
        assert not result.allowed
        assert result.mandate_id is None

    def test_wrong_root_key_rejected(self, minted):
        other = Ed25519PrivateKey.generate()
        other_pem = other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        result = authorize_presentation(
            minted.token,
            root_public_key_hex(other_pem),
            agent_id=AGENT_ID,
            amount_cents=100,
            scope="spend:commerce",
            now=NOW,
        )
        assert not result.allowed
