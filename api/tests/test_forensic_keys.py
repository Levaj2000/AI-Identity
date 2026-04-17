"""End-to-end tests for GET /.well-known/ai-identity-public-keys.json."""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _pem_private(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class TestJWKSEndpoint:
    def test_returns_empty_keys_when_unconfigured(self, client, monkeypatch):
        """No signer configured → empty keys list (not 500)."""
        from common.config.settings import settings

        monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
        monkeypatch.setattr(settings, "forensic_signing_key_pem", "", raising=False)

        resp = client.get("/.well-known/ai-identity-public-keys.json")
        assert resp.status_code == 200
        assert resp.json() == {"keys": []}

    def test_publishes_local_key(self, client, monkeypatch):
        from common.config.settings import settings

        key = ec.generate_private_key(ec.SECP256R1())
        monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
        monkeypatch.setattr(settings, "forensic_signing_key_pem", _pem_private(key), raising=False)

        resp = client.get("/.well-known/ai-identity-public-keys.json")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["keys"]) == 1
        jwk = body["keys"][0]
        assert jwk["kty"] == "EC"
        assert jwk["kid"].startswith("local:")

    def test_cache_control_and_content_type(self, client, monkeypatch):
        """Endpoint is public + cacheable; downstream CDNs depend on this."""
        from common.config.settings import settings

        key = ec.generate_private_key(ec.SECP256R1())
        monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
        monkeypatch.setattr(settings, "forensic_signing_key_pem", _pem_private(key), raising=False)

        resp = client.get("/.well-known/ai-identity-public-keys.json")
        assert "max-age" in resp.headers.get("cache-control", "")
        assert resp.headers.get("content-type", "").startswith("application/jwk-set+json")

    def test_no_auth_required(self, client, monkeypatch):
        """JWKS is public by design — no X-API-Key header supplied."""
        from common.config.settings import settings

        monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
        monkeypatch.setattr(settings, "forensic_signing_key_pem", "", raising=False)

        resp = client.get("/.well-known/ai-identity-public-keys.json")
        assert resp.status_code == 200
