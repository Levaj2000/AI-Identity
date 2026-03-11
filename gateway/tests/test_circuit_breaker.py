"""Tests for the circuit breaker pattern — state transitions and failure tracking.

SECURITY-CRITICAL: The circuit breaker is part of fail-closed enforcement.
These tests verify that:
  - The breaker trips after the configured failure threshold
  - An open breaker denies all requests
  - The recovery period transitions to half-open
  - A failed probe re-opens the breaker
  - A successful probe closes the breaker
"""

import time
from unittest.mock import patch

from gateway.app.circuit_breaker import CircuitBreaker, CircuitState


def _make_breaker(**kwargs):
    """Create a circuit breaker with test-friendly defaults."""
    defaults = {
        "failure_threshold": 5,
        "window_seconds": 60,
        "recovery_seconds": 10,
        "name": "test",
    }
    defaults.update(kwargs)
    return CircuitBreaker(**defaults)


# ── State Transitions ──────────────────────────────────────────────────


class TestCircuitBreakerStates:
    """Verify the breaker transitions: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def test_initial_state_is_closed(self):
        """Breaker starts in CLOSED state."""
        cb = _make_breaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_stays_closed_below_threshold(self):
        """Fewer failures than threshold keeps breaker CLOSED."""
        cb = _make_breaker(failure_threshold=5)

        for _ in range(4):
            cb.record_failure()

        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_trips_at_threshold(self):
        """Exactly N failures in the window trips the breaker to OPEN."""
        cb = _make_breaker(failure_threshold=5)

        for _ in range(5):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_open_denies_all(self):
        """An open breaker denies all requests."""
        cb = _make_breaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        # Multiple checks — all denied
        for _ in range(10):
            assert cb.can_execute() is False

    def test_recovery_transitions_to_half_open(self):
        """After recovery_seconds, OPEN transitions to HALF_OPEN."""
        cb = _make_breaker(failure_threshold=3, recovery_seconds=5)

        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Capture real time BEFORE patching, then advance past recovery
        future_time = time.monotonic() + 6
        with patch("gateway.app.circuit_breaker.time.monotonic", return_value=future_time):
            assert cb.state == CircuitState.HALF_OPEN
            assert cb.can_execute() is True

    def test_half_open_success_closes(self):
        """A successful probe in HALF_OPEN closes the breaker."""
        cb = _make_breaker(failure_threshold=3, recovery_seconds=5)

        for _ in range(3):
            cb.record_failure()

        # Advance past recovery
        future_time = time.monotonic() + 6
        with patch("gateway.app.circuit_breaker.time.monotonic", return_value=future_time):
            assert cb.state == CircuitState.HALF_OPEN

            # Successful probe
            cb.record_success()
            assert cb.state == CircuitState.CLOSED
            assert cb.can_execute() is True

    def test_half_open_failure_reopens(self):
        """A failed probe in HALF_OPEN re-opens the breaker."""
        cb = _make_breaker(failure_threshold=3, recovery_seconds=5)

        for _ in range(3):
            cb.record_failure()

        # Advance past recovery
        future_time = time.monotonic() + 6
        with patch("gateway.app.circuit_breaker.time.monotonic", return_value=future_time):
            assert cb.state == CircuitState.HALF_OPEN

            # Failed probe
            cb.record_failure()
            assert cb.state == CircuitState.OPEN
            assert cb.can_execute() is False


# ── Sliding Window ─────────────────────────────────────────────────────


class TestSlidingWindow:
    """Verify that old failures expire from the window."""

    def test_old_failures_expire(self):
        """Failures outside the window are pruned and don't count."""
        cb = _make_breaker(failure_threshold=3, window_seconds=10)

        # Record 2 failures at current time
        cb.record_failure()
        cb.record_failure()

        # Advance time past the window, then record 1 more
        future_time = time.monotonic() + 11
        with patch("gateway.app.circuit_breaker.time.monotonic", return_value=future_time):
            # Record 1 more failure — should NOT trip (old 2 expired)
            cb.record_failure()
            assert cb.state == CircuitState.CLOSED

    def test_failures_within_window_accumulate(self):
        """Failures within the window accumulate normally."""
        cb = _make_breaker(failure_threshold=3, window_seconds=60)

        cb.record_failure()
        cb.record_failure()
        cb.record_failure()

        assert cb.state == CircuitState.OPEN


# ── Reset ──────────────────────────────────────────────────────────────


class TestCircuitBreakerReset:
    """Verify manual reset returns breaker to clean CLOSED state."""

    def test_reset_from_open(self):
        """Manual reset closes an open breaker."""
        cb = _make_breaker(failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_reset_clears_failure_count(self):
        """Reset clears the failure history."""
        cb = _make_breaker(failure_threshold=5)

        for _ in range(4):
            cb.record_failure()

        cb.reset()

        # One more failure should NOT trip (history cleared)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED


# ── Status Reporting ───────────────────────────────────────────────────


class TestCircuitBreakerStatus:
    """Verify the status snapshot for monitoring."""

    def test_status_closed(self):
        """Status reflects CLOSED state with zero failures."""
        cb = _make_breaker()
        status = cb.status

        assert status.state == CircuitState.CLOSED
        assert status.failure_count == 0
        assert status.opened_at is None

    def test_status_after_failures(self):
        """Status reflects failure count."""
        cb = _make_breaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()

        status = cb.status
        assert status.state == CircuitState.CLOSED
        assert status.failure_count == 2
        assert status.last_failure_time is not None

    def test_status_open(self):
        """Status reflects OPEN state with opened_at timestamp."""
        cb = _make_breaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()

        status = cb.status
        assert status.state == CircuitState.OPEN
        assert status.opened_at is not None
