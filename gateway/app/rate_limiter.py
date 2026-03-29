"""Pre-policy sliding-window rate limiter for the AI Identity gateway.

SECURITY-CRITICAL: Enforces per-IP and per-agent_id request limits before
any policy evaluation or DB access occurs. This is a pre-policy defense —
rate limit denials are NOT written to the HMAC audit chain (that's for
policy decisions only). Uses standard Python logging for observability.

Design principles:
  - SLIDING WINDOW: avoids boundary-burst problem of fixed windows.
  - REDIS-BACKED: uses sorted sets for cross-worker shared state.
  - IN-MEMORY FALLBACK: if REDIS_URL is empty or Redis is unreachable,
    falls back to per-process deques (graceful degradation).
  - FAIL-OPEN on internal error: if the limiter itself errors, allow the
    request through (don't block traffic due to a limiter bug).
"""

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass

from common.config.settings import settings

logger = logging.getLogger("ai_identity.gateway.rate_limiter")


# ── Result ──────────────────────────────────────────────────────────────


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    limit: int  # X-RateLimit-Limit
    remaining: int  # X-RateLimit-Remaining
    reset_after: float  # seconds until oldest entry expires (X-RateLimit-Reset)
    retry_after: float | None  # seconds to wait (only set when denied)


# ── In-Memory Backend (fallback) ────────────────────────────────────────


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter using per-process deques.

    Used as the fallback when Redis is unavailable or not configured.

    Args:
        per_ip_limit: Max requests per window per IP address.
        per_key_limit: Max requests per window per agent_id.
        window_seconds: Sliding window duration in seconds.
        cleanup_threshold: Number of tracked entities before auto-cleanup triggers.
    """

    def __init__(
        self,
        *,
        per_ip_limit: int,
        per_key_limit: int,
        window_seconds: float,
        cleanup_threshold: int = 10_000,
    ):
        self._per_ip_limit = per_ip_limit
        self._per_key_limit = per_key_limit
        self._window_seconds = window_seconds
        self._cleanup_threshold = cleanup_threshold

        self._ip_windows: dict[str, deque[float]] = {}
        self._key_windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check_ip(self, ip: str) -> RateLimitResult:
        """Check and record a request against the per-IP limit."""
        with self._lock:
            return self._check_and_record(
                windows=self._ip_windows,
                key=ip,
                limit=self._per_ip_limit,
            )

    def check_key(self, key: str) -> RateLimitResult:
        """Check and record a request against the per-key (agent_id) limit."""
        with self._lock:
            return self._check_and_record(
                windows=self._key_windows,
                key=key,
                limit=self._per_key_limit,
            )

    def _check_and_record(
        self,
        windows: dict[str, deque[float]],
        key: str,
        limit: int,
    ) -> RateLimitResult:
        """Core sliding window algorithm. Must be called with lock held."""
        now = time.monotonic()
        cutoff = now - self._window_seconds

        if key not in windows:
            windows[key] = deque()

        window = windows[key]

        while window and window[0] < cutoff:
            window.popleft()

        count = len(window)

        if window:
            reset_after = max(0.0, self._window_seconds - (now - window[0]))
        else:
            reset_after = self._window_seconds

        if count >= limit:
            retry_after = max(0.01, self._window_seconds - (now - window[0]))
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_after=reset_after,
                retry_after=retry_after,
            )

        window.append(now)
        remaining = limit - count - 1

        total_keys = len(self._ip_windows) + len(self._key_windows)
        if total_keys > self._cleanup_threshold:
            self._cleanup_stale(cutoff)

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=max(0, remaining),
            reset_after=reset_after,
            retry_after=None,
        )

    def _cleanup_stale(self, cutoff: float) -> None:
        """Remove entries for IPs/keys with no recent requests. Lock must be held."""
        removed = 0
        for windows_dict in (self._ip_windows, self._key_windows):
            stale_keys = [k for k, v in windows_dict.items() if not v or v[-1] < cutoff]
            for k in stale_keys:
                del windows_dict[k]
            removed += len(stale_keys)

        if removed:
            logger.debug("Rate limiter cleanup: removed %d stale entries", removed)

    def reset(self) -> None:
        """Clear all tracking data. For testing and manual recovery."""
        with self._lock:
            self._ip_windows.clear()
            self._key_windows.clear()


# ── Redis Backend ───────────────────────────────────────────────────────


class RedisRateLimiter:
    """Sliding window rate limiter backed by Redis sorted sets.

    Shared across all Gunicorn workers via a Redis instance. Each check is
    an atomic pipeline: ZREMRANGEBYSCORE + ZADD + ZCARD + ZRANGE + EXPIRE.

    Uses wall-clock time (time.time) instead of monotonic time because the
    sorted set is shared across processes.
    """

    def __init__(
        self,
        *,
        redis_url: str,
        per_ip_limit: int,
        per_key_limit: int,
        window_seconds: float,
    ):
        import redis as redis_lib

        self._per_ip_limit = per_ip_limit
        self._per_key_limit = per_key_limit
        self._window_seconds = window_seconds

        pool = redis_lib.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=10,
        )
        self._client = redis_lib.Redis(connection_pool=pool)
        self._client.ping()  # fail fast if unreachable

    def check_ip(self, ip: str) -> RateLimitResult:
        """Check and record a request against the per-IP limit."""
        return self._check_redis("ip", ip, self._per_ip_limit)

    def check_key(self, key: str) -> RateLimitResult:
        """Check and record a request against the per-key (agent_id) limit."""
        return self._check_redis("key", key, self._per_key_limit)

    def _check_redis(self, namespace: str, key: str, limit: int) -> RateLimitResult:
        """Sorted-set sliding window: prune → add → count → check."""
        redis_key = f"rl:{namespace}:{key}"
        now = time.time()
        cutoff = now - self._window_seconds
        member = f"{now}:{uuid.uuid4().hex[:8]}"

        pipe = self._client.pipeline(transaction=True)
        pipe.zremrangebyscore(redis_key, "-inf", cutoff)
        pipe.zadd(redis_key, {member: now})
        pipe.zcard(redis_key)
        pipe.zrange(redis_key, 0, 0, withscores=True)
        pipe.expire(redis_key, int(self._window_seconds) + 1)
        results = pipe.execute()

        count = results[2]
        oldest_entries = results[3]
        oldest_score = oldest_entries[0][1] if oldest_entries else now

        reset_after = max(0.0, self._window_seconds - (now - oldest_score))

        if count > limit:
            # Over limit — remove the entry we just added and deny
            self._client.zrem(redis_key, member)
            retry_after = max(0.01, self._window_seconds - (now - oldest_score))
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_after=reset_after,
                retry_after=retry_after,
            )

        remaining = limit - count
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=max(0, remaining),
            reset_after=reset_after,
            retry_after=None,
        )

    def reset(self) -> None:
        """Clear all rate limit keys. For testing and manual recovery."""
        keys = self._client.keys("rl:*")
        if keys:
            self._client.delete(*keys)


# ── Facade (auto-selects backend) ──────────────────────────────────────


class RateLimiter:
    """Rate limiter facade — uses Redis if configured, in-memory otherwise.

    Provides the same public API (check_ip, check_key, reset) regardless of
    backend. On Redis errors at runtime, falls back to the in-memory limiter
    for that request and logs a warning once.
    """

    def __init__(
        self,
        *,
        per_ip_limit: int | None = None,
        per_key_limit: int | None = None,
        window_seconds: float | None = None,
        cleanup_threshold: int = 10_000,
    ):
        per_ip = per_ip_limit if per_ip_limit is not None else settings.rate_limit_per_ip
        per_key = per_key_limit if per_key_limit is not None else settings.rate_limit_per_key
        window = (
            window_seconds if window_seconds is not None else settings.rate_limit_window_seconds
        )

        # Always create the in-memory fallback
        self._fallback = InMemoryRateLimiter(
            per_ip_limit=per_ip,
            per_key_limit=per_key,
            window_seconds=window,
            cleanup_threshold=cleanup_threshold,
        )

        self._backend: InMemoryRateLimiter | RedisRateLimiter

        # Try Redis if configured
        if settings.redis_url:
            try:
                self._backend = RedisRateLimiter(
                    redis_url=settings.redis_url,
                    per_ip_limit=per_ip,
                    per_key_limit=per_key,
                    window_seconds=window,
                )
                logger.info("Rate limiter using Redis backend")
            except Exception:
                logger.warning(
                    "Redis unavailable at startup, falling back to in-memory rate limiter",
                    exc_info=True,
                )
                self._backend = self._fallback
        else:
            logger.info("No REDIS_URL configured, using in-memory rate limiter")
            self._backend = self._fallback

        self._redis_warned = False

    def check_ip(self, ip: str) -> RateLimitResult:
        """Check and record a request against the per-IP limit."""
        try:
            return self._backend.check_ip(ip)
        except Exception:
            return self._handle_error("check_ip", ip)

    def check_key(self, key: str) -> RateLimitResult:
        """Check and record a request against the per-key (agent_id) limit."""
        try:
            return self._backend.check_key(key)
        except Exception:
            return self._handle_error("check_key", key)

    def _handle_error(self, method: str, key: str) -> RateLimitResult:
        """Log once and fall back to in-memory for this request."""
        if not self._redis_warned:
            logger.warning(
                "Redis error during rate limit check, falling back to in-memory",
                exc_info=True,
            )
            self._redis_warned = True
        return getattr(self._fallback, method)(key)

    def reset(self) -> None:
        """Clear all tracking data on both backends."""
        self._backend.reset()
        if self._backend is not self._fallback:
            self._fallback.reset()


# ── Module-Level Instance ───────────────────────────────────────────────
# Shared across all requests (thread-safe).
# Follows the same pattern as policy_circuit_breaker in enforce.py.

rate_limiter = RateLimiter()
