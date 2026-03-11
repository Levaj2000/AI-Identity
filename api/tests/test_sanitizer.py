"""Tests for API key and credential sanitization.

SECURITY-CRITICAL: These tests verify that secrets never leak into
logs, error responses, or external payloads.
"""

import logging

from common.auth.keys import generate_api_key
from common.auth.sanitizer import mask_key, sanitize, sanitize_url

# ── sanitize() — API key masking ────────────────────────────────────────


class TestSanitizeKeys:
    """Verify aid_sk_ and aid_admin_ keys are masked in arbitrary text."""

    def test_masks_agent_key_in_text(self):
        key = "aid_sk_abc123def456ghi789jkl012mno345pqr678stu"
        text = f"Failed to authenticate with key {key}"
        result = sanitize(text)
        assert "aid_sk_abc1********" in result
        assert key not in result

    def test_masks_admin_key_in_text(self):
        key = "aid_admin_xyz789abc123def456ghi789jkl012mno345"
        text = f"Admin key: {key}"
        result = sanitize(text)
        assert "aid_admin_xyz7********" in result
        assert key not in result

    def test_masks_generated_key(self):
        key = generate_api_key()
        text = f"Created agent with key {key}"
        result = sanitize(text)
        assert key not in result
        assert "aid_sk_" in result  # Prefix preserved
        assert "********" in result  # Masked suffix

    def test_masks_multiple_keys_in_same_string(self):
        key1 = "aid_sk_abc123def456ghi789jkl012mno345pqr678stu"
        key2 = "aid_sk_xyz987uvw654rst321pon098mlk765jih432gfe"
        text = f"Old key: {key1}, New key: {key2}"
        result = sanitize(text)
        assert key1 not in result
        assert key2 not in result
        assert result.count("********") >= 2

    def test_preserves_text_without_keys(self):
        text = "Agent created successfully with id 550e8400-e29b-41d4-a716-446655440000"
        assert sanitize(text) == text

    def test_preserves_key_prefix_reference(self):
        # Short references like "aid_sk_" alone should not cause issues
        text = "Keys use the aid_sk_ prefix"
        result = sanitize(text)
        assert "aid_sk_" in result

    def test_empty_string(self):
        assert sanitize("") == ""

    def test_none_returns_none(self):
        assert sanitize(None) is None


# ── sanitize() — SHA-256 hash masking ───────────────────────────────────


class TestSanitizeHashes:
    """Verify SHA-256 hex hashes are masked."""

    def test_masks_sha256_hash(self):
        hash_val = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
        text = f"Key hash: {hash_val}"
        result = sanitize(text)
        assert hash_val not in result
        assert "a1b2c3d4********" in result

    def test_does_not_mask_short_hex(self):
        # UUIDs and other short hex strings should not be masked
        text = "Agent id: 550e8400-e29b-41d4-a716-446655440000"
        result = sanitize(text)
        assert "550e8400" in result


# ── sanitize_url() — database URL masking ───────────────────────────────


class TestSanitizeUrl:
    """Verify database passwords are masked in connection URLs."""

    def test_masks_postgresql_password(self):
        url = "postgresql://admin:super_s3cret_pw@db.neon.tech:5432/mydb"
        result = sanitize_url(url)
        assert "super_s3cret_pw" not in result
        assert "****" in result
        assert "admin" in result  # Username preserved
        assert "db.neon.tech" in result  # Host preserved

    def test_masks_postgres_scheme(self):
        url = "postgres://user:password123@localhost:5432/ai_identity"
        result = sanitize_url(url)
        assert "password123" not in result
        assert "****" in result

    def test_preserves_url_without_password(self):
        url = "postgresql://localhost:5432/ai_identity"
        result = sanitize_url(url)
        assert result == url

    def test_masks_redis_password(self):
        url = "redis://default:my_redis_pw@redis.render.com:6379"
        result = sanitize_url(url)
        assert "my_redis_pw" not in result

    def test_masks_url_embedded_in_text(self):
        text = "Connecting to postgresql://admin:s3cret@host:5432/db now"
        result = sanitize(text)
        assert "s3cret" not in result


# ── sanitize() — env var secret patterns ────────────────────────────────


class TestSanitizeEnvSecrets:
    """Verify env-var-style secrets are masked."""

    def test_masks_api_key_env_var(self):
        text = "API_KEY=sk-proj-abc123def456ghi789jkl012"
        result = sanitize(text)
        assert "sk-proj-abc123def456ghi789jkl012" not in result
        assert "API_KEY=" in result

    def test_masks_secret_env_var(self):
        text = "SECRET=my_super_secret_value_12345"
        result = sanitize(text)
        assert "my_super_secret_value_12345" not in result

    def test_masks_token_env_var(self):
        text = "TOKEN: ghp_abc123def456ghi789jkl012mno345"
        result = sanitize(text)
        assert "ghp_abc123def456ghi789jkl012mno345" not in result


# ── mask_key() — single key masking ─────────────────────────────────────


class TestMaskKey:
    """Verify mask_key() works on isolated key strings."""

    def test_masks_agent_key(self):
        key = generate_api_key()
        masked = mask_key(key)
        assert masked.startswith("aid_sk_")
        assert masked.endswith("********")
        assert len(masked) < len(key)
        assert key not in masked

    def test_masks_unknown_format(self):
        key = "some-random-long-api-key-value-that-is-not-ours"
        masked = mask_key(key)
        assert masked == "some-ran********"

    def test_masks_short_key(self):
        key = "short"
        masked = mask_key(key)
        assert masked == "********"


# ── Log sanitization integration ────────────────────────────────────────


class TestLogSanitization:
    """Verify the SanitizingFilter scrubs secrets from log output."""

    def test_log_filter_masks_key_in_message(self, caplog):
        """Keys passed to logger.info() must be masked in output."""
        from common.config.logging import SanitizingFilter

        test_logger = logging.getLogger("test.sanitizer")
        test_logger.addFilter(SanitizingFilter())
        test_logger.setLevel(logging.DEBUG)

        key = "aid_sk_testkey123456789abcdef0123456789abcdef"
        with caplog.at_level(logging.INFO, logger="test.sanitizer"):
            test_logger.info("Authenticating with key %s", key)

        # The raw key must NOT appear in any log record
        for record in caplog.records:
            assert key not in record.getMessage()
            assert "aid_sk_test********" in record.getMessage()

    def test_log_filter_masks_database_url(self, caplog):
        """Database URLs with passwords must be masked in log output."""
        from common.config.logging import SanitizingFilter

        test_logger = logging.getLogger("test.sanitizer.db")
        test_logger.addFilter(SanitizingFilter())
        test_logger.setLevel(logging.DEBUG)

        db_url = "postgresql://admin:s3cret_pw@db.neon.tech:5432/mydb"
        with caplog.at_level(logging.INFO, logger="test.sanitizer.db"):
            test_logger.info("Connecting to %s", db_url)

        for record in caplog.records:
            assert "s3cret_pw" not in record.getMessage()

    def test_log_filter_masks_key_in_exception(self, caplog):
        """Exception tracebacks containing keys must be sanitized."""
        from common.config.logging import SanitizingFilter

        test_logger = logging.getLogger("test.sanitizer.exc")
        test_logger.addFilter(SanitizingFilter())
        test_logger.setLevel(logging.DEBUG)

        key = "aid_sk_exception_key_abcdef0123456789abcdef01"
        try:
            raise ValueError(f"Invalid key: {key}")
        except ValueError:
            with caplog.at_level(logging.ERROR, logger="test.sanitizer.exc"):
                test_logger.exception("Auth failed")

        for record in caplog.records:
            assert key not in record.getMessage()
            # Exception text is sanitized by the filter
            if record.exc_text:
                assert key not in record.exc_text


# ── Error response sanitization ─────────────────────────────────────────


class TestErrorResponseSanitization:
    """Verify API error responses never contain raw keys."""

    def test_401_does_not_leak_key(self, client):
        """Authentication failure must not echo the key back."""
        bad_key = "aid_sk_bad_key_attempt_12345678901234567890"
        resp = client.get("/api/v1/agents", headers={"X-API-Key": bad_key})
        assert resp.status_code == 401
        body = resp.text
        assert bad_key not in body

    def test_404_does_not_leak_key(self, client, auth_headers):
        """Agent-not-found must not leak any key material."""
        resp = client.get(
            "/api/v1/agents/00000000-0000-0000-0000-000000000099",
            headers=auth_headers,
        )
        assert resp.status_code in (404, 401)
        body = resp.text
        assert "aid_sk_" not in body or "********" in body

    def test_create_agent_response_key_is_intentional(self, client, auth_headers):
        """The show-once api_key in create response is the ONLY place a full key appears."""
        resp = client.post(
            "/api/v1/agents",
            headers=auth_headers,
            json={"name": "Sanitizer Test Agent"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # This is the one place a full key IS returned (by design)
        assert data["api_key"].startswith("aid_sk_")

    def test_list_keys_never_returns_full_key(self, client, auth_headers):
        """List keys endpoint must only return prefix, never full key or hash."""
        # Create an agent first
        create_resp = client.post(
            "/api/v1/agents",
            headers=auth_headers,
            json={"name": "Key List Test"},
        )
        agent_id = create_resp.json()["agent"]["id"]

        # List keys
        resp = client.get(f"/api/v1/agents/{agent_id}/keys", headers=auth_headers)
        assert resp.status_code == 200
        for key_item in resp.json()["items"]:
            # key_prefix is short (12 chars), never the full key
            assert len(key_item["key_prefix"]) <= 12
            assert "key_hash" not in key_item
