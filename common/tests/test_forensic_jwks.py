"""Unit tests for the JWKS builder.

Covers both backends:

* Local PEM — derives a JWK from the one configured key; verifiable
  by converting back to a pub key and running it through the existing
  ``verify_envelope`` helper end-to-end.
* KMS — exercises the ``list_crypto_key_versions`` / ``get_public_key``
  iteration, including skipping destroyed versions and tagging state.

KMS tests use a hand-rolled fake rather than ``google.cloud.kms_v1``
mocks so they stay fast and deterministic.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.forensic.jwks import build_jwks


def _pem_private(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def _pem_public(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _settings(**overrides):
    """Build a minimal settings-like object with only the fields we read."""
    defaults = {
        "forensic_signing_key_id": "",
        "forensic_signing_key_pem": "",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── Local PEM backend ───────────────────────────────────────────────


class TestLocalBackend:
    def test_empty_when_no_backend_configured(self):
        assert build_jwks(_settings()) == {"keys": []}

    def test_both_backends_set_returns_empty(self):
        """Defensive: refuse to publish keys when the signer config is ambiguous."""
        out = build_jwks(
            _settings(
                forensic_signing_key_id="projects/x/locations/y/keyRings/z/cryptoKeys/k/cryptoKeyVersions/1",
                forensic_signing_key_pem="dummy",
            )
        )
        assert out == {"keys": []}

    def test_local_pem_produces_one_jwk(self):
        key = ec.generate_private_key(ec.SECP256R1())
        out = build_jwks(_settings(forensic_signing_key_pem=_pem_private(key)))

        assert len(out["keys"]) == 1
        jwk = out["keys"][0]
        assert jwk["kty"] == "EC"
        assert jwk["crv"] == "P-256"
        assert jwk["alg"] == "ES256"
        assert jwk["use"] == "sig"
        assert jwk["kid"].startswith("local:")
        assert jwk["ai_identity:state"] == "enabled"

    def test_jwk_coordinates_match_public_key(self):
        """x/y decode to the same EC point as the source key."""
        key = ec.generate_private_key(ec.SECP256R1())
        jwk = build_jwks(_settings(forensic_signing_key_pem=_pem_private(key)))["keys"][0]

        nums = key.public_key().public_numbers()
        x_bytes = nums.x.to_bytes(32, "big")
        y_bytes = nums.y.to_bytes(32, "big")

        # base64url decode (accept missing padding)
        def _dec(s: str) -> bytes:
            pad = "=" * (-len(s) % 4)
            return base64.urlsafe_b64decode(s + pad)

        assert _dec(jwk["x"]) == x_bytes
        assert _dec(jwk["y"]) == y_bytes

    def test_kid_matches_signer_module(self):
        """The published kid must equal the signer's signer_key_id
        so envelopes sign and verify against the same identity.
        """
        from common.forensic.signer import get_forensic_signer

        key = ec.generate_private_key(ec.SECP256R1())
        s = _settings(forensic_signing_key_pem=_pem_private(key))
        jwk = build_jwks(s)["keys"][0]
        signer = get_forensic_signer(s)
        assert jwk["kid"] == signer.key_id


# ── KMS backend ──────────────────────────────────────────────────────


class _FakeKMSVersion:
    def __init__(self, name: str, state: str, create_time=None):
        self.name = name
        self.state = SimpleNamespace(name=state)
        self.create_time = create_time


class _FakeKMSPublicKey:
    def __init__(self, pem: bytes):
        self.pem = pem.decode("utf-8")


class _FakeKMSClient:
    """Stand-in for ``kms_v1.KeyManagementServiceClient``.

    Returns the configured version list on ``list_crypto_key_versions``
    and the configured PEM for each version on ``get_public_key``.
    """

    def __init__(self, versions: list[tuple[str, str, ec.EllipticCurvePrivateKey]]):
        # versions: [(name_suffix, state, private_key_to_derive_pub)]
        self._versions = versions

    def list_crypto_key_versions(self, *, request):
        parent = request["parent"]
        return iter(
            _FakeKMSVersion(
                name=f"{parent}/cryptoKeyVersions/{idx + 1}",
                state=state,
            )
            for idx, (_name_suffix, state, _pk) in enumerate(self._versions)
        )

    def get_public_key(self, *, request):
        name = request["name"]
        idx = int(name.rsplit("/", 1)[-1]) - 1
        pk = self._versions[idx][2]
        return _FakeKMSPublicKey(_pem_public(pk))


@pytest.fixture
def stub_kms_client(monkeypatch):
    """Patch ``_kms_jwks`` to use a fake client rather than google-cloud-kms."""

    def _install(versions):
        fake = _FakeKMSClient(versions)

        class _ImportStub:
            KeyManagementServiceClient = lambda self_stub: fake  # noqa: E731

        # The code does ``from google.cloud import kms_v1`` inside the
        # function; we swap the attribute for the duration of the test.
        class _ModuleStub:
            kms_v1 = _ImportStub()

        monkeypatch.setitem(
            __import__("sys").modules,
            "google.cloud",
            _ModuleStub(),
        )

    return _install


class TestKMSBackend:
    def test_lists_all_enabled_and_disabled_versions(self, stub_kms_client):
        k1 = ec.generate_private_key(ec.SECP256R1())
        k2 = ec.generate_private_key(ec.SECP256R1())
        k3 = ec.generate_private_key(ec.SECP256R1())
        stub_kms_client(
            [
                ("v1", "ENABLED", k1),
                ("v2", "DISABLED", k2),
                ("v3", "DESTROYED", k3),  # must be omitted
            ]
        )

        parent = "projects/p/locations/l/keyRings/r/cryptoKeys/k"
        key_version_id = f"{parent}/cryptoKeyVersions/1"
        out = build_jwks(_settings(forensic_signing_key_id=key_version_id))

        # 2 entries (enabled + disabled); destroyed skipped
        assert len(out["keys"]) == 2
        states = [k["ai_identity:state"] for k in out["keys"]]
        assert "enabled" in states
        assert "disabled" in states
        assert "destroyed" not in states

        # kids are full resource paths, not just version numbers
        for k in out["keys"]:
            assert k["kid"].startswith(parent + "/cryptoKeyVersions/")
            assert k["kty"] == "EC"
            assert k["crv"] == "P-256"

    def test_malformed_key_id_returns_empty(self, stub_kms_client):
        """Typo'd env var → empty JWKS, not a 500.

        The endpoint stays up so verifiers can distinguish "this server
        has no keys yet" from "the server is down".
        """
        stub_kms_client([])  # should never be called
        out = build_jwks(_settings(forensic_signing_key_id="not-a-kms-path"))
        assert out == {"keys": []}
