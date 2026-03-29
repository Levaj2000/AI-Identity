"""Tests for pre-policy rate limiting — per-IP and per-key sliding window limits.

SECURITY-CRITICAL: These tests verify that the gateway enforces request
rate limits before any policy evaluation or database access occurs.

Verifies:
  - Per-IP rate limiting (101st request in 1s window gets 429)
  - Per-key/agent_id rate limiting (61st request gets 429)
  - Rate limit headers on ALL responses (X-RateLimit-*)
  - Retry-After header on 429 responses
  - Health/info endpoints are exempt
  - Kill switch (rate_limit_enabled=False) bypasses all limits
  - Multiple IPs and keys are tracked independently
  - Stale entry cleanup reclaims memory
  - Thread safety under concurrent access
  - X-Forwarded-For header correctly parsed
"""

import threading
import time
import uuid
from unittest.mock import patch

from gateway.app.rate_limiter import RateLimiter

# ── Unit Tests: RateLimiter Class ───────────────────────────────────────


class TestRateLimiterUnit:
    """Unit tests for the RateLimiter class directly (no HTTP)."""

    def test_allows_requests_under_limit(self):
        """Requests under the limit are all allowed."""
        rl = RateLimiter(per_ip_limit=10, per_key_limit=5, window_seconds=1)
        for _ in range(10):
            result = rl.check_ip("1.2.3.4")
            assert result.allowed is True

    def test_denies_request_at_ip_limit(self):
        """The (limit+1)th request from same IP is denied."""
        rl = RateLimiter(per_ip_limit=5, per_key_limit=60, window_seconds=1)
        for _ in range(5):
            result = rl.check_ip("1.2.3.4")
            assert result.allowed is True

        # 6th request — denied
        result = rl.check_ip("1.2.3.4")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_denies_request_at_key_limit(self):
        """The (limit+1)th request for same key is denied."""
        rl = RateLimiter(per_ip_limit=100, per_key_limit=3, window_seconds=1)
        for _ in range(3):
            result = rl.check_key("agent-abc")
            assert result.allowed is True

        result = rl.check_key("agent-abc")
        assert result.allowed is False
        assert result.remaining == 0

    def test_remaining_decrements(self):
        """Remaining count decrements with each request."""
        rl = RateLimiter(per_ip_limit=5, per_key_limit=60, window_seconds=1)
        for i in range(5):
            result = rl.check_ip("1.2.3.4")
            assert result.remaining == 5 - i - 1

    def test_limit_field_reflects_configured_limit(self):
        """The limit field in the result matches the configured limit."""
        rl = RateLimiter(per_ip_limit=42, per_key_limit=17, window_seconds=1)
        assert rl.check_ip("x").limit == 42
        assert rl.check_key("y").limit == 17

    def test_reset_clears_all_counters(self):
        """reset() clears all IP and key tracking."""
        rl = RateLimiter(per_ip_limit=2, per_key_limit=2, window_seconds=1)
        rl.check_ip("1.2.3.4")
        rl.check_ip("1.2.3.4")
        assert rl.check_ip("1.2.3.4").allowed is False  # at limit

        rl.reset()
        assert rl.check_ip("1.2.3.4").allowed is True  # counters cleared


# ── Sliding Window Tests ────────────────────────────────────────────────


class TestSlidingWindow:
    """Verify that the sliding window expires old entries correctly."""

    def test_requests_expire_after_window(self):
        """Requests outside the window don't count toward the limit."""
        rl = RateLimiter(per_ip_limit=3, per_key_limit=60, window_seconds=1)

        # Fill to limit
        for _ in range(3):
            rl.check_ip("1.2.3.4")
        assert rl.check_ip("1.2.3.4").allowed is False

        # Advance time past window
        future = time.monotonic() + 1.1
        with patch("gateway.app.rate_limiter.time.monotonic", return_value=future):
            result = rl.check_ip("1.2.3.4")
            assert result.allowed is True  # old requests expired
            assert result.remaining == 2  # only 1 used in new window


# ── Isolation Tests ─────────────────────────────────────────────────────


class TestIsolation:
    """Verify that different IPs and keys are tracked independently."""

    def test_different_ips_independent(self):
        """Exhausting one IP's limit doesn't affect another."""
        rl = RateLimiter(per_ip_limit=2, per_key_limit=60, window_seconds=1)
        rl.check_ip("1.1.1.1")
        rl.check_ip("1.1.1.1")
        assert rl.check_ip("1.1.1.1").allowed is False

        # Different IP should still work
        assert rl.check_ip("2.2.2.2").allowed is True

    def test_different_keys_independent(self):
        """Exhausting one key's limit doesn't affect another."""
        rl = RateLimiter(per_ip_limit=100, per_key_limit=2, window_seconds=1)
        rl.check_key("agent-a")
        rl.check_key("agent-a")
        assert rl.check_key("agent-a").allowed is False

        assert rl.check_key("agent-b").allowed is True

    def test_ip_and_key_limits_independent(self):
        """IP limit and key limit are checked separately."""
        rl = RateLimiter(per_ip_limit=5, per_key_limit=3, window_seconds=1)
        # After 3 key requests, key is exhausted but IP still has headroom
        for _ in range(3):
            rl.check_key("agent-x")
        assert rl.check_key("agent-x").allowed is False
        # IP check still allows (separate tracking)
        assert rl.check_ip("1.2.3.4").allowed is True


# ── Stale Entry Cleanup ────────────────────────────────────────────────


class TestStaleEntryCleanup:
    """Verify that stale entries are cleaned up to prevent memory leaks."""

    def test_cleanup_removes_expired_entries(self):
        """Entries with all-expired timestamps are removed during cleanup."""
        rl = RateLimiter(
            per_ip_limit=100,
            per_key_limit=100,
            window_seconds=1,
            cleanup_threshold=2,
        )
        # Create entries for multiple IPs
        rl.check_ip("1.1.1.1")
        rl.check_ip("2.2.2.2")

        # Advance time so entries expire, then trigger cleanup via a new request
        future = time.monotonic() + 2.0
        with patch("gateway.app.rate_limiter.time.monotonic", return_value=future):
            rl.check_ip("3.3.3.3")  # triggers cleanup (threshold=2, now 3 keys)

        # The internal dict should have been cleaned
        backend = rl._fallback
        with backend._lock:
            assert "1.1.1.1" not in backend._ip_windows
            assert "2.2.2.2" not in backend._ip_windows
            assert "3.3.3.3" in backend._ip_windows


# ── Thread Safety ───────────────────────────────────────────────────────


class TestThreadSafety:
    """Verify thread safety under concurrent access."""

    def test_concurrent_access_respects_limit(self):
        """Multiple threads hitting the same IP don't exceed the limit."""
        rl = RateLimiter(per_ip_limit=50, per_key_limit=60, window_seconds=1)
        results: list = []
        barrier = threading.Barrier(10)

        def worker():
            barrier.wait()
            for _ in range(10):
                results.append(rl.check_ip("shared-ip"))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed = sum(1 for r in results if r.allowed)
        denied = sum(1 for r in results if not r.allowed)
        # Exactly 50 should be allowed, 50 denied
        assert allowed == 50
        assert denied == 50


# ── HTTP Middleware Tests ───────────────────────────────────────────────


class TestRateLimitMiddlewareHTTP:
    """Test rate limiting through the full HTTP middleware stack."""

    def test_per_ip_limit_returns_429(self, client, test_agent, test_policy):
        """101st request from same IP returns 429.

        Uses multiple agent_ids (rotate every 50) to avoid hitting the
        per-key limit (60) before the per-IP limit (100).
        """
        agent_ids = [str(test_agent.id), str(uuid.uuid4()), str(uuid.uuid4())]

        for i in range(100):
            resp = client.post(
                "/gateway/enforce",
                params={
                    "agent_id": agent_ids[i // 50],
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )
            # Some may return 404 for fake agents, but the rate limiter
            # runs BEFORE enforce, so the request is still counted
            assert resp.status_code != 429, f"Request {i + 1} should not be rate limited"

        # 101st request — any agent_id, same IP
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"]["code"] == "rate_limit_exceeded"

    def test_per_key_limit_returns_429(self, client, test_agent, test_policy):
        """61st request with same agent_id returns 429."""
        for i in range(60):
            resp = client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )
            assert resp.status_code == 200, f"Request {i + 1} should succeed"

        # 61st request — same agent_id
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )
        assert resp.status_code == 429

    def test_429_includes_retry_after(self, client, test_agent, test_policy):
        """429 responses include Retry-After header."""
        for _ in range(60):
            client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )

        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )
        assert resp.status_code == 429
        assert "retry-after" in resp.headers
        retry_after = int(resp.headers["retry-after"])
        assert retry_after >= 1

    def test_rate_limit_headers_on_success(self, client, test_agent, test_policy):
        """Successful responses include X-RateLimit-* headers."""
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )
        assert resp.status_code == 200
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers
        assert "x-ratelimit-reset" in resp.headers

    def test_health_exempt_from_rate_limit(self, client, test_agent, test_policy):
        """GET /health is not rate limited even after IP is exhausted."""
        # Exhaust the IP limit
        for i in range(100):
            client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(uuid.uuid4()) if i >= 50 else str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )

        # Health endpoint should still work
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root_exempt_from_rate_limit(self, client, test_agent, test_policy):
        """GET / is not rate limited even after IP is exhausted."""
        for i in range(100):
            client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(uuid.uuid4()) if i >= 50 else str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )

        resp = client.get("/")
        assert resp.status_code == 200


# ── Disabled Rate Limiter ───────────────────────────────────────────────


class TestRateLimitDisabled:
    """Test that rate limiting can be disabled via settings."""

    def test_disabled_allows_all(self, client, test_agent, test_policy):
        """When rate_limit_enabled=False, no rate limiting occurs."""
        from common.config.settings import settings as app_settings

        original = app_settings.rate_limit_enabled
        try:
            # Use object.__setattr__ since Settings is frozen by Pydantic
            object.__setattr__(app_settings, "rate_limit_enabled", False)
            for _ in range(200):
                resp = client.post(
                    "/gateway/enforce",
                    params={
                        "agent_id": str(test_agent.id),
                        "endpoint": "/v1/chat",
                        "method": "POST",
                    },
                )
                assert resp.status_code == 200
        finally:
            object.__setattr__(app_settings, "rate_limit_enabled", original)

    def test_disabled_no_rate_limit_headers(self, client, test_agent, test_policy):
        """When rate_limit_enabled=False, no X-RateLimit headers are added."""
        from common.config.settings import settings as app_settings

        original = app_settings.rate_limit_enabled
        try:
            object.__setattr__(app_settings, "rate_limit_enabled", False)
            resp = client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )
            assert "x-ratelimit-limit" not in resp.headers
        finally:
            object.__setattr__(app_settings, "rate_limit_enabled", original)


# ── Response Format ─────────────────────────────────────────────────────


class TestRateLimitResponseFormat:
    """Verify the 429 response matches the gateway error format."""

    def test_429_response_format(self, client, test_agent, test_policy):
        """429 response matches gateway error JSON structure."""
        for _ in range(60):
            client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
            )

        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
        )
        assert resp.status_code == 429
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "rate_limit_exceeded"
        assert "Try again" in data["error"]["message"]


# ── X-Forwarded-For Tests ──────────────────────────────────────────────


class TestXForwardedFor:
    """Test IP extraction from X-Forwarded-For header."""

    def test_uses_first_ip_from_forwarded_header(self, client, test_agent, test_policy):
        """X-Forwarded-For header's first IP is used for rate limiting."""
        # Exhaust IP limit for a specific forwarded IP (use multiple agents)
        for i in range(100):
            client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(uuid.uuid4()) if i >= 50 else str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
                headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"},
            )

        # 101st from same forwarded IP should be blocked
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
            headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"},
        )
        assert resp.status_code == 429

    def test_different_forwarded_ip_is_independent(self, client, test_agent, test_policy):
        """Different X-Forwarded-For IPs are tracked independently."""
        # Use up some requests from IP-A
        for _ in range(50):
            client.post(
                "/gateway/enforce",
                params={
                    "agent_id": str(test_agent.id),
                    "endpoint": "/v1/chat",
                    "method": "POST",
                },
                headers={"X-Forwarded-For": "203.0.113.1"},
            )

        # IP-B should still have its full quota
        resp = client.post(
            "/gateway/enforce",
            params={
                "agent_id": str(test_agent.id),
                "endpoint": "/v1/chat",
                "method": "POST",
            },
            headers={"X-Forwarded-For": "203.0.113.2"},
        )
        assert resp.status_code == 200
        # Should have nearly full remaining (first request from this IP)
        remaining = int(resp.headers.get("x-ratelimit-remaining", 0))
        assert remaining > 0
