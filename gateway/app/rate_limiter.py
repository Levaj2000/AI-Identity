"""Pre-policy sliding-window rate limiter for the AI Identity gateway.

SECURITY-CRITICAL: Enforces per-IP and per-agent_id request limits before
any policy evaluation or DB access occurs. This is a pre-policy defense —
rate limit denials are NOT written to the HMAC audit chain (that's for
policy decisions only). Uses standard Python logging for observability.

Design principles:
  - SLIDING WINDOW: avoids boundary-burst problem of fixed windows.
  - THREAD-SAFE: single threading.Lock guards all state.
  - IN-MEMORY: Phase 1 uses deques; Phase 2 migrates to Redis sorted sets.
  - FAIL-OPEN on internal error: if the limiter itself errors, allow the
    request through (don't block traffic due to a limiter bug).
"""

import logging
import threading
import time
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


# ── Core Limiter ────────────────────────────────────────────────────────


class RateLimiter:
    """Thread-safe sliding window rate limiter with per-IP and per-key tracking.

    Uses deques of monotonic timestamps per tracked entity (IP or agent_id).
    Follows the same thread-safety pattern as circuit_breaker.py.

    Args:
        per_ip_limit: Max requests per window per IP address.
        per_key_limit: Max requests per window per agent_id.
        window_seconds: Sliding window duration in seconds.
        cleanup_threshold: Number of tracked entities before auto-cleanup triggers.
    """

    def __init__(
        self,
        *,
        per_ip_limit: int | None = None,
        per_key_limit: int | None = None,
        window_seconds: float | None = None,
        cleanup_threshold: int = 10_000,
    ):
        self._per_ip_limit = (
            per_ip_limit if per_ip_limit is not None else settings.rate_limit_per_ip
        )
        self._per_key_limit = (
            per_key_limit if per_key_limit is not None else settings.rate_limit_per_key
        )
        self._window_seconds = (
            window_seconds if window_seconds is not None else settings.rate_limit_window_seconds
        )
        self._cleanup_threshold = cleanup_threshold

        # Separate dicts for IP and key tracking
        self._ip_windows: dict[str, deque[float]] = {}
        self._key_windows: dict[str, deque[float]] = {}

        # Single lock for all state (simple, correct; Phase 2 Redis removes contention)
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
        """Core sliding window algorithm. Must be called with lock held.

        Algorithm:
        1. Get or create the deque for this key.
        2. Prune timestamps older than window_seconds.
        3. If len(deque) >= limit → DENY.
        4. Else → append now, ALLOW.
        5. Compute remaining, reset_after, retry_after.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds

        if key not in windows:
            windows[key] = deque()

        window = windows[key]

        # Prune expired timestamps — O(k) where k = expired entries
        while window and window[0] < cutoff:
            window.popleft()

        count = len(window)

        # Compute reset_after: time until the oldest entry in window expires
        if window:
            reset_after = max(0.0, self._window_seconds - (now - window[0]))
        else:
            reset_after = self._window_seconds

        if count >= limit:
            # DENIED — compute retry_after (time until oldest expires, freeing a slot)
            retry_after = max(0.01, self._window_seconds - (now - window[0]))
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_after=reset_after,
                retry_after=retry_after,
            )

        # ALLOWED — record this request
        window.append(now)
        remaining = limit - count - 1  # -1 because we just added one

        # Trigger cleanup if we have too many tracked entities
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
            stale_keys = [
                k
                for k, v in windows_dict.items()
                if not v or v[-1] < cutoff  # empty or last request is expired
            ]
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


# ── Module-Level Instance ───────────────────────────────────────────────
# Shared across all requests (thread-safe).
# Follows the same pattern as policy_circuit_breaker in enforce.py.

rate_limiter = RateLimiter()
