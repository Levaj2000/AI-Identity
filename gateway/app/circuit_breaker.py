"""Thread-safe circuit breaker for fail-closed gateway enforcement.

The circuit breaker tracks policy evaluation failures and trips open when
the failure threshold is reached, causing all subsequent requests to be
denied until the recovery period elapses.

States:
    CLOSED  — Normal operation. Failures are counted.
    OPEN    — Tripped. All requests denied immediately (503).
    HALF_OPEN — Recovery probe. One request is allowed through;
                success → CLOSED, failure → OPEN.

SECURITY-CRITICAL: This module is part of the fail-closed enforcement.
When the breaker is OPEN, the gateway MUST deny all requests rather than
allowing them through (fail-closed, not fail-open).
"""

import enum
import logging
import threading
import time
from dataclasses import dataclass

from common.config.settings import settings

logger = logging.getLogger("ai_identity.gateway.circuit_breaker")


class CircuitState(enum.StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStatus:
    """Snapshot of circuit breaker state for monitoring."""

    state: CircuitState
    failure_count: int
    last_failure_time: float | None
    last_success_time: float | None
    opened_at: float | None


class CircuitBreaker:
    """Thread-safe circuit breaker with sliding window failure tracking.

    Args:
        failure_threshold: Number of failures in the window to trip the breaker.
        window_seconds: Sliding window for counting failures.
        recovery_seconds: How long the breaker stays open before allowing a probe.
        name: Identifier for logging (e.g., "policy-engine").
    """

    def __init__(
        self,
        *,
        failure_threshold: int | None = None,
        window_seconds: int | None = None,
        recovery_seconds: int | None = None,
        name: str = "default",
    ):
        self._failure_threshold = (
            failure_threshold
            if failure_threshold is not None
            else settings.circuit_breaker_failure_threshold
        )
        self._window_seconds = (
            window_seconds
            if window_seconds is not None
            else settings.circuit_breaker_window_seconds
        )
        self._recovery_seconds = (
            recovery_seconds
            if recovery_seconds is not None
            else settings.circuit_breaker_recovery_seconds
        )
        self._name = name

        # Internal state (guarded by lock)
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_timestamps: list[float] = []
        self._opened_at: float | None = None
        self._last_failure_time: float | None = None
        self._last_success_time: float | None = None

    # ── Public API ────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        """Current breaker state (may transition OPEN → HALF_OPEN on read)."""
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    @property
    def status(self) -> CircuitBreakerStatus:
        """Snapshot of the breaker's current status for monitoring."""
        with self._lock:
            self._maybe_transition_to_half_open()
            return CircuitBreakerStatus(
                state=self._state,
                failure_count=len(self._failure_timestamps),
                last_failure_time=self._last_failure_time,
                last_success_time=self._last_success_time,
                opened_at=self._opened_at,
            )

    def can_execute(self) -> bool:
        """Check whether a request should be allowed through.

        Returns True if the breaker is CLOSED or HALF_OPEN (probe).
        Returns False if the breaker is OPEN — caller MUST deny the request.

        SECURITY: This is the fail-closed gate. When False, the gateway
        returns 503 without forwarding the request.
        """
        with self._lock:
            self._maybe_transition_to_half_open()

            if self._state == CircuitState.CLOSED:
                return True

            # HALF_OPEN allows one probe request; OPEN denies everything
            return self._state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        """Record a successful policy evaluation.

        If HALF_OPEN, transitions to CLOSED (recovery complete).
        """
        with self._lock:
            now = time.monotonic()
            self._last_success_time = now

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_timestamps.clear()
                self._opened_at = None
                logger.info(
                    "Circuit breaker '%s' recovered → CLOSED",
                    self._name,
                )

    def record_failure(self) -> None:
        """Record a failed policy evaluation.

        Adds a timestamp to the sliding window. If the threshold is
        reached, trips the breaker to OPEN.

        If HALF_OPEN, immediately re-opens the breaker.
        """
        with self._lock:
            now = time.monotonic()
            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — reopen
                self._state = CircuitState.OPEN
                self._opened_at = now
                logger.warning(
                    "Circuit breaker '%s' probe failed → OPEN (recovery reset)",
                    self._name,
                )
                return

            # CLOSED — add failure to sliding window
            self._failure_timestamps.append(now)
            self._prune_old_failures(now)

            if len(self._failure_timestamps) >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = now
                logger.critical(
                    "Circuit breaker '%s' TRIPPED → OPEN "
                    "(%d failures in %ds window). "
                    "All requests will be denied for %ds.",
                    self._name,
                    len(self._failure_timestamps),
                    self._window_seconds,
                    self._recovery_seconds,
                )

    def reset(self) -> None:
        """Force-reset the breaker to CLOSED. For testing and manual recovery."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_timestamps.clear()
            self._opened_at = None
            logger.info("Circuit breaker '%s' manually reset → CLOSED", self._name)

    # ── Internal ──────────────────────────────────────────────────────

    def _prune_old_failures(self, now: float) -> None:
        """Remove failure timestamps outside the sliding window.

        Must be called with lock held.
        """
        cutoff = now - self._window_seconds
        self._failure_timestamps = [
            t for t in self._failure_timestamps if t >= cutoff
        ]

    def _maybe_transition_to_half_open(self) -> None:
        """Check if an OPEN breaker should transition to HALF_OPEN.

        Must be called with lock held.
        """
        if self._state != CircuitState.OPEN:
            return
        if self._opened_at is None:
            return

        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self._recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            logger.info(
                "Circuit breaker '%s' recovery period elapsed → HALF_OPEN "
                "(allowing probe request)",
                self._name,
            )
