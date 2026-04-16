"""Regression tests for the audit-write-failure visibility path added after
the 2026-04-16 incident. The core property we lock in:

  If `create_audit_entry` raises, the gateway bumps
  `ai_identity_audit_write_failures_total{service="gateway",kind=…}` and
  does NOT re-raise.

A non-zero rate on this counter is the always-on alert that would have
caught the incident on day one instead of day three.
"""

from __future__ import annotations

import psycopg2
import pytest

from common.observability.metrics import (
    audit_write_failures_total,
    classify_audit_write_failure,
    record_audit_write_failure,
)


def _sample(service: str, kind: str) -> float:
    """Return the current counter value for (service, kind); 0 if never bumped."""
    for metric in audit_write_failures_total.collect():
        for s in metric.samples:
            if s.name.endswith("_total") and s.labels == {"service": service, "kind": kind}:
                return s.value
    return 0.0


def test_classifier_recognizes_schema_mismatches() -> None:
    # The exact exception the 2026-04-16 incident produced.
    exc = psycopg2.errors.UndefinedColumn('column "org_id" of relation "audit_log" does not exist')
    assert classify_audit_write_failure(exc) == "schema"


def test_classifier_recognizes_integrity_concerns() -> None:
    exc = RuntimeError("entry_hash mismatch — HMAC chain corrupt")
    assert classify_audit_write_failure(exc) == "integrity"


def test_classifier_falls_back_to_unknown() -> None:
    exc = TimeoutError("db connection timed out")
    assert classify_audit_write_failure(exc) == "unknown"


def test_record_audit_write_failure_bumps_counter() -> None:
    before = _sample("gateway", "schema")
    record_audit_write_failure("gateway", kind="schema")
    after = _sample("gateway", "schema")
    assert after == pytest.approx(before + 1.0)


def test_record_audit_write_failure_never_raises(monkeypatch) -> None:
    # Simulate prometheus_client itself blowing up; the call must still
    # return cleanly so observability problems don't change enforcement.
    def boom(**kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("prometheus exploded")

    monkeypatch.setattr(audit_write_failures_total, "labels", boom)
    record_audit_write_failure("gateway", kind="unknown")  # does not raise
