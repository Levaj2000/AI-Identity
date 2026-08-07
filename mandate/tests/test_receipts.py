"""Tests for common/biscuit/receipts.py — mint, verify, forgery cases."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from common.biscuit import mint_receipt, verify_receipt
from common.biscuit.tokens import mint_mandate_biscuit


def _pem() -> str:
    return (
        Ed25519PrivateKey.generate()
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )


@pytest.fixture(scope="module")
def root_pem() -> str:
    return _pem()


PAYLOAD = {
    "kind": "mandate_draw_receipt",
    "mandate_id": "mnd_ab12cd34",
    "revocation_id": "deadbeef",
    "amount_cents": 1_500,
    "decision": "allow",
}


class TestMint:
    def test_mint_stamps_and_signs(self, root_pem):
        bundle = mint_receipt(root_pem, PAYLOAD)
        assert bundle["algorithm"] == "ed25519-jcs"
        assert bundle["receipt"]["issued_at"]
        assert bundle["receipt"]["mandate_id"] == "mnd_ab12cd34"

    def test_no_key_raises(self):
        with pytest.raises(ValueError):
            mint_receipt("", PAYLOAD)

    def test_receipt_key_matches_biscuit_root_key(self, root_pem):
        # One trust anchor, both directions: whoever can verify the token
        # can verify the receipt.
        import datetime as dt

        minted = mint_mandate_biscuit(
            private_key_pem=root_pem,
            mandate_id="mnd_ab12cd34",
            subject_agent_id="a",
            subject_org_id="o",
            scope=["spend:commerce"],
            valid_from=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        )
        bundle = mint_receipt(root_pem, PAYLOAD)
        assert bundle["public_key"] == minted.root_public_key


class TestVerify:
    def test_round_trip(self, root_pem):
        bundle = mint_receipt(root_pem, PAYLOAD)
        assert verify_receipt(bundle, bundle["public_key"])

    def test_tampered_payload_fails(self, root_pem):
        bundle = mint_receipt(root_pem, PAYLOAD)
        bundle["receipt"]["amount_cents"] = 1  # delegate shaving the record
        assert not verify_receipt(bundle, bundle["public_key"])

    def test_forged_key_substitution_fails(self, root_pem):
        # A forger re-signs a doctored receipt with their own key and swaps
        # in their public key — the verifier trusts only the root key.
        trusted = mint_receipt(root_pem, PAYLOAD)["public_key"]
        forged = mint_receipt(_pem(), {**PAYLOAD, "amount_cents": 1})
        assert not verify_receipt(forged, trusted)

    def test_garbage_bundle_fails_closed(self, root_pem):
        trusted = mint_receipt(root_pem, PAYLOAD)["public_key"]
        assert not verify_receipt({}, trusted)
        assert not verify_receipt({"receipt": {}, "algorithm": "none"}, trusted)
