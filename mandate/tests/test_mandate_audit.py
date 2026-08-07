"""Audit-write posture tests for _write_mandate_audit.

Locks down the fail-close stance documented in the helper's docstring:
the only guarded step is the subject-id parse (non-platform subjects are
skipped — no org chain to join); a failing create_audit_entry propagates
so the caller's HTTP request fails rather than completing unaudited.

Like the other mandate tests, no MongoDB and no HTTP stack — the helper
is called directly with create_audit_entry monkeypatched in the router's
namespace (it is imported by name there).
"""

import uuid

import pytest

from mandate.app.routers import mandates as mandates_router

AGENT_UUID = uuid.uuid4()


def _call(subject_agent_id: str) -> None:
    mandates_router._write_mandate_audit(
        db=object(),
        subject_agent_id=subject_agent_id,
        endpoint="/api/v1/mandates",
        decision="mandate_granted",
        metadata={"mandate_id": "mnd_cafef00d"},
    )


class TestWriteMandateAudit:
    def test_audit_write_failure_propagates(self, monkeypatch):
        """Fail-closed: a broken audit chain must fail the caller's request."""

        def boom(*args, **kwargs):
            raise RuntimeError("audit chain unavailable")

        monkeypatch.setattr(mandates_router, "create_audit_entry", boom)
        with pytest.raises(RuntimeError, match="audit chain unavailable"):
            _call(str(AGENT_UUID))

    def test_non_platform_subject_skipped_without_error(self, monkeypatch, caplog):
        """Non-UUID subject ids have no org chain to join: log + skip, no raise."""
        calls = []
        monkeypatch.setattr(
            mandates_router, "create_audit_entry", lambda *a, **kw: calls.append(kw)
        )
        with caplog.at_level("WARNING", logger="ai_identity.mandate.router"):
            _call("did:example:external-agent")
        assert calls == []
        assert "mandate audit skipped" in caplog.text

    def test_platform_subject_written_with_parsed_uuid(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            mandates_router, "create_audit_entry", lambda db, **kw: calls.append(kw)
        )
        _call(str(AGENT_UUID))
        assert len(calls) == 1
        assert calls[0]["agent_id"] == AGENT_UUID
        assert calls[0]["decision"] == "mandate_granted"
