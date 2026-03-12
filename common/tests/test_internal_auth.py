"""Unit tests for HMAC-SHA256 internal service authentication.

Tests the sign/verify roundtrip, replay protection, tamper detection,
and the fail-closed behavior when the key is not configured.

Sprint Item #52 — acceptance criteria:
  - Missing HMAC = 401
  - Expired requests rejected
  - Secret from env var only
"""

import time
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from common.auth.internal import (
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    require_internal_auth,
    sign_request,
    verify_request,
)

# Fixed test key — NOT a real secret
TEST_KEY = "test-internal-key-for-unit-tests-only-do-not-use-in-production"


# ── Sign + Verify Roundtrip ─────────────────────────────────────────────


class TestSignAndVerify:
    """Happy-path roundtrip: sign → verify → True."""

    def test_sign_and_verify_roundtrip(self):
        """POST request with body signs and verifies successfully."""
        body = b'{"agent_id": "abc123"}'
        headers = sign_request("POST", "/api/v1/agents/lookup", body=body, key=TEST_KEY)

        assert verify_request(
            method="POST",
            path="/api/v1/agents/lookup",
            body=body,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_empty_body_works(self):
        """GET request with no body (None) signs and verifies."""
        headers = sign_request("GET", "/health", body=None, key=TEST_KEY)

        assert verify_request(
            method="GET",
            path="/health",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_empty_bytes_body_matches_none(self):
        """body=b'' and body=None produce the same signature."""
        headers_none = sign_request("GET", "/test", body=None, key=TEST_KEY)
        headers_empty = sign_request("GET", "/test", body=b"", key=TEST_KEY)

        assert headers_none[HEADER_SIGNATURE] == headers_empty[HEADER_SIGNATURE]

    def test_different_methods(self):
        """All standard HTTP methods sign and verify correctly."""
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            headers = sign_request(method, "/test", key=TEST_KEY)
            assert verify_request(
                method=method,
                path="/test",
                body=None,
                signature=headers[HEADER_SIGNATURE],
                timestamp_str=headers[HEADER_TIMESTAMP],
                key=TEST_KEY,
            ), f"Failed for method {method}"

    def test_returns_both_headers(self):
        """sign_request returns exactly the two expected header keys."""
        headers = sign_request("GET", "/test", key=TEST_KEY)
        assert set(headers.keys()) == {HEADER_SIGNATURE, HEADER_TIMESTAMP}
        assert len(headers[HEADER_SIGNATURE]) == 64  # SHA-256 hex digest
        assert headers[HEADER_TIMESTAMP].isdigit()


# ── Replay Protection ───────────────────────────────────────────────────


class TestReplayProtection:
    """Timestamp enforcement — ±30 second window."""

    def test_expired_timestamp_rejected(self):
        """Request signed 31 seconds ago is rejected."""
        old_ts = time.time() - 31
        headers = sign_request("GET", "/test", key=TEST_KEY, timestamp=old_ts)

        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_future_timestamp_rejected(self):
        """Request signed 31 seconds in the future is rejected."""
        future_ts = time.time() + 31
        headers = sign_request("GET", "/test", key=TEST_KEY, timestamp=future_ts)

        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_boundary_timestamp_accepted(self):
        """Request signed exactly 30 seconds ago is still valid."""
        # Use a fixed "now" to avoid flakiness
        now = time.time()
        ts = now - 30  # exactly at the boundary

        headers = sign_request("GET", "/test", key=TEST_KEY, timestamp=ts)

        with patch("common.auth.internal.time") as mock_time:
            mock_time.time.return_value = now
            assert verify_request(
                method="GET",
                path="/test",
                body=None,
                signature=headers[HEADER_SIGNATURE],
                timestamp_str=headers[HEADER_TIMESTAMP],
                key=TEST_KEY,
            )


# ── Tamper Detection ────────────────────────────────────────────────────


class TestTamperDetection:
    """Any modification to the signed request must invalidate the HMAC."""

    def test_wrong_key_rejected(self):
        """Signing with key A, verifying with key B fails."""
        headers = sign_request("GET", "/test", key="key-a-secret")

        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key="key-b-different",
        )

    def test_tampered_body_rejected(self):
        """Changing the body after signing invalidates the HMAC."""
        headers = sign_request("POST", "/test", body=b"original", key=TEST_KEY)

        assert not verify_request(
            method="POST",
            path="/test",
            body=b"tampered",
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_tampered_path_rejected(self):
        """Changing the path after signing invalidates the HMAC."""
        headers = sign_request("GET", "/api/v1/agents", key=TEST_KEY)

        assert not verify_request(
            method="GET",
            path="/api/v1/admin/delete-all",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_tampered_method_rejected(self):
        """Changing GET to DELETE after signing invalidates the HMAC."""
        headers = sign_request("GET", "/test", key=TEST_KEY)

        assert not verify_request(
            method="DELETE",
            path="/test",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )

    def test_tampered_signature_rejected(self):
        """Flipping a character in the signature invalidates it."""
        headers = sign_request("GET", "/test", key=TEST_KEY)
        sig = headers[HEADER_SIGNATURE]
        # Flip the first character
        tampered = ("0" if sig[0] != "0" else "1") + sig[1:]

        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=tampered,
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )


# ── Fail-Closed ─────────────────────────────────────────────────────────


class TestFailClosed:
    """Empty/missing key must reject all requests."""

    def test_empty_key_verify_rejected(self):
        """verify_request with empty key returns False."""
        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature="anything",
            timestamp_str=str(int(time.time())),
            key="",
        )

    def test_sign_empty_key_raises(self):
        """sign_request with empty key raises ValueError."""
        with pytest.raises(ValueError, match="INTERNAL_SERVICE_KEY"):
            sign_request("GET", "/test", key="")

    def test_settings_default_empty_key(self):
        """With default settings (empty key), verify_request returns False."""
        with patch("common.auth.internal.settings") as mock_settings:
            mock_settings.internal_service_key = ""
            assert not verify_request(
                method="GET",
                path="/test",
                body=None,
                signature="anything",
                timestamp_str=str(int(time.time())),
            )


# ── Invalid Input ───────────────────────────────────────────────────────


class TestInvalidInput:
    """Edge cases and malformed inputs."""

    def test_invalid_timestamp_format_rejected(self):
        """Non-numeric timestamp string is rejected."""
        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature="anything",
            timestamp_str="not-a-number",
            key=TEST_KEY,
        )

    def test_none_timestamp_rejected(self):
        """None timestamp is rejected (TypeError caught)."""
        assert not verify_request(
            method="GET",
            path="/test",
            body=None,
            signature="anything",
            timestamp_str=None,
            key=TEST_KEY,
        )

    def test_method_case_insensitive(self):
        """Signing with 'post' and verifying with 'POST' works (normalized)."""
        headers = sign_request("post", "/test", key=TEST_KEY)

        assert verify_request(
            method="POST",
            path="/test",
            body=None,
            signature=headers[HEADER_SIGNATURE],
            timestamp_str=headers[HEADER_TIMESTAMP],
            key=TEST_KEY,
        )


# ── FastAPI Dependency Integration ──────────────────────────────────────


class TestFastAPIDependency:
    """Integration tests with a minimal FastAPI app."""

    @pytest.fixture
    def internal_app(self):
        """Minimal FastAPI app with an internal-auth-protected endpoint."""
        app = FastAPI()

        @app.post("/internal/test", dependencies=[Depends(require_internal_auth)])
        async def internal_post():
            return {"status": "ok"}

        @app.get("/internal/test", dependencies=[Depends(require_internal_auth)])
        async def internal_get():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def internal_client(self, internal_app):
        return TestClient(internal_app)

    def test_missing_signature_returns_401(self, internal_client):
        """POST with no auth headers returns 401."""
        resp = internal_client.post("/internal/test", json={"data": "test"})
        assert resp.status_code == 401

    def test_missing_timestamp_returns_401(self, internal_client):
        """POST with signature but no timestamp returns 401."""
        resp = internal_client.post(
            "/internal/test",
            json={"data": "test"},
            headers={HEADER_SIGNATURE: "fake-sig"},
        )
        assert resp.status_code == 401

    def test_valid_request_returns_200(self, internal_client):
        """Properly signed POST request returns 200."""
        body = b'{"data": "test"}'
        headers = sign_request("POST", "/internal/test", body=body, key=TEST_KEY)

        with patch("common.auth.internal.settings") as mock_settings:
            mock_settings.internal_service_key = TEST_KEY
            resp = internal_client.post(
                "/internal/test",
                content=body,
                headers=headers,
            )

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_expired_request_returns_401(self, internal_client):
        """Request signed 31 seconds ago returns 401."""
        body = b'{"data": "test"}'
        old_ts = time.time() - 31
        headers = sign_request("POST", "/internal/test", body=body, key=TEST_KEY, timestamp=old_ts)

        with patch("common.auth.internal.settings") as mock_settings:
            mock_settings.internal_service_key = TEST_KEY
            resp = internal_client.post(
                "/internal/test",
                content=body,
                headers=headers,
            )

        assert resp.status_code == 401

    def test_get_request_no_body_returns_200(self, internal_client):
        """GET request with no body, properly signed, returns 200."""
        headers = sign_request("GET", "/internal/test", key=TEST_KEY)

        with patch("common.auth.internal.settings") as mock_settings:
            mock_settings.internal_service_key = TEST_KEY
            resp = internal_client.get("/internal/test", headers=headers)

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
