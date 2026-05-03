"""Audit hook for Ada — gateway/enforce ping per tool call.

Validates the dogfood story (Sprint 12 #327, Insight #74):
- Each tool call → POST to AI Identity gateway/enforce with Ada's agent_id
- Allow → tool runs (callback returns None)
- Deny → tool short-circuited via ADK's before_tool_callback contract
- Network error / 5xx → tool short-circuited (synchronous-enough)
- Nonce included in headers (forward-compat with backend nonce check)
- Auth disabled (default) → callback no-ops, launcher unaffected

`httpx.post` is patched so tests never hit the network.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest
from ada import audit as audit_mod
from ada.audit import (
    AuditDecision,
    AuditError,
    after_tool_audit_callback,
    audit_action,
    before_tool_audit_callback,
)


class _FakeTool:
    """Minimal stand-in for ADK's BaseTool — only `.name` is read."""

    def __init__(self, name: str) -> None:
        self.name = name


def _resp(status: int, body: dict[str, Any] | None = None) -> object:
    class _R:
        status_code = status

        @staticmethod
        def json() -> dict[str, Any]:
            return body or {}

    return _R()


def _post_returning(status: int, body: dict[str, Any] | None = None):
    def _post(*args: Any, **kwargs: Any) -> object:  # noqa: ARG001
        return _resp(status, body)

    return _post


def _post_raising(exc: Exception):
    def _post(*args: Any, **kwargs: Any) -> object:  # noqa: ARG001
        raise exc

    return _post


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Audit required + agent_id + runtime key set."""
    monkeypatch.setenv("ADA_REQUIRE_AUDIT", "1")
    monkeypatch.setenv("ADA_AGENT_ID", "agt_ada_uuid")
    monkeypatch.setenv("AI_IDENTITY_GATEWAY_URL", "https://gateway.test")
    monkeypatch.setenv("AI_IDENTITY_API_KEY", "aid_sk_runtime_test")


@pytest.fixture
def disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Audit disabled (the default — preserves the launcher experience)."""
    monkeypatch.delenv("ADA_REQUIRE_AUDIT", raising=False)


class TestAuditAction:
    def test_allow_returns_decision(self, configured: None) -> None:  # noqa: ARG002
        post = _post_returning(200, {"decision": "allow", "status_code": 200, "message": "ok"})
        with patch.object(audit_mod.httpx, "post", post):
            decision = audit_action("read_file")
        assert decision.decision == "allow"
        assert decision.status_code == 200
        assert decision.nonce  # non-empty
        assert decision.latency_ms >= 0

    def test_deny_returns_decision(self, configured: None) -> None:  # noqa: ARG002
        post = _post_returning(403, {"decision": "deny", "status_code": 403})
        with patch.object(audit_mod.httpx, "post", post):
            decision = audit_action("read_file")
        assert decision.decision == "deny"
        assert decision.status_code == 403

    def test_5xx_raises_audit_error(self, configured: None) -> None:  # noqa: ARG002
        with (
            patch.object(audit_mod.httpx, "post", _post_returning(503, {})),
            pytest.raises(AuditError, match="5xx"),
        ):
            audit_action("read_file")

    def test_network_error_raises_audit_error(self, configured: None) -> None:  # noqa: ARG002
        with (
            patch.object(
                audit_mod.httpx,
                "post",
                _post_raising(httpx.ConnectError("connection refused")),
            ),
            pytest.raises(AuditError, match="unreachable"),
        ):
            audit_action("read_file")

    def test_timeout_raises_audit_error(self, configured: None) -> None:  # noqa: ARG002
        with (
            patch.object(
                audit_mod.httpx,
                "post",
                _post_raising(httpx.TimeoutException("read timeout")),
            ),
            pytest.raises(AuditError),
        ):
            audit_action("read_file")

    def test_missing_agent_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ADA_AGENT_ID", raising=False)
        with pytest.raises(AuditError, match="ADA_AGENT_ID"):
            audit_action("read_file")

    def test_includes_nonce_header(self, configured: None) -> None:  # noqa: ARG002
        captured: dict[str, Any] = {}

        def _post(*args: Any, **kwargs: Any) -> object:
            captured.update(kwargs)
            return _resp(200, {"decision": "allow"})

        with patch.object(audit_mod.httpx, "post", _post):
            audit_action("read_file")

        headers = captured["headers"]
        assert "X-Audit-Nonce" in headers
        assert len(headers["X-Audit-Nonce"]) >= 32  # UUID4 string

    def test_includes_runtime_key_header(self, configured: None) -> None:  # noqa: ARG002
        captured: dict[str, Any] = {}

        def _post(*args: Any, **kwargs: Any) -> object:
            captured.update(kwargs)
            return _resp(200, {"decision": "allow"})

        with patch.object(audit_mod.httpx, "post", _post):
            audit_action("read_file")

        assert captured["headers"]["X-Agent-Key"] == "aid_sk_runtime_test"

    def test_endpoint_encodes_tool_name(self, configured: None) -> None:  # noqa: ARG002
        captured: dict[str, Any] = {}

        def _post(*args: Any, **kwargs: Any) -> object:
            captured.update(kwargs)
            return _resp(200, {"decision": "allow"})

        with patch.object(audit_mod.httpx, "post", _post):
            audit_action("search_code")

        assert captured["params"]["endpoint"] == "/ada/tools/search_code"
        assert captured["params"]["agent_id"] == "agt_ada_uuid"
        assert captured["params"]["key_type"] == "runtime"


class TestBeforeToolCallback:
    def test_disabled_returns_none(self, disabled: None) -> None:  # noqa: ARG002
        # No httpx call should happen when audit disabled — patch to fail loudly if it does.
        with patch.object(audit_mod.httpx, "post", _post_raising(AssertionError("called"))):
            result = before_tool_audit_callback(_FakeTool("read_file"), {}, None)
        assert result is None

    def test_allow_returns_none(self, configured: None) -> None:  # noqa: ARG002
        with patch.object(audit_mod.httpx, "post", _post_returning(200, {"decision": "allow"})):
            result = before_tool_audit_callback(_FakeTool("read_file"), {}, None)
        assert result is None  # tool runs

    def test_deny_returns_error_dict(self, configured: None) -> None:  # noqa: ARG002
        with patch.object(audit_mod.httpx, "post", _post_returning(403, {"decision": "deny"})):
            result = before_tool_audit_callback(_FakeTool("read_file"), {}, None)
        assert result is not None
        assert result["status"] == "error"
        assert "denied" in result["error_message"].lower()

    def test_network_error_returns_error_dict(self, configured: None) -> None:  # noqa: ARG002
        with patch.object(
            audit_mod.httpx,
            "post",
            _post_raising(httpx.ConnectError("refused")),
        ):
            result = before_tool_audit_callback(_FakeTool("read_file"), {}, None)
        assert result is not None
        assert result["status"] == "error"
        assert "unreachable" in result["error_message"].lower()

    def test_5xx_returns_error_dict(self, configured: None) -> None:  # noqa: ARG002
        with patch.object(audit_mod.httpx, "post", _post_returning(503)):
            result = before_tool_audit_callback(_FakeTool("read_file"), {}, None)
        assert result is not None
        assert result["status"] == "error"
        assert "unreachable" in result["error_message"].lower() or "5xx" in result["error_message"]


class TestAfterToolCallback:
    def test_disabled_returns_none(self, disabled: None) -> None:  # noqa: ARG002
        result = after_tool_audit_callback(_FakeTool("read_file"), {}, None, {"status": "success"})
        assert result is None

    def test_enabled_returns_none_to_preserve_response(self, configured: None) -> None:  # noqa: ARG002
        # The after-callback emits a structured log but must not modify the tool result.
        result = after_tool_audit_callback(
            _FakeTool("read_file"), {}, None, {"status": "success", "content": "..."}
        )
        assert result is None


class TestAgentWiring:
    def test_root_agent_has_audit_callbacks(self) -> None:
        # Smoke: importing agent.py wires the audit callbacks. If a future
        # refactor accidentally drops the kwarg, this catches it.
        from ada.agent import root_agent

        assert root_agent.before_tool_callback is before_tool_audit_callback
        assert root_agent.after_tool_callback is after_tool_audit_callback


class TestAuditDecisionDataclass:
    def test_immutable(self) -> None:
        d = AuditDecision(decision="allow", status_code=200, latency_ms=1.5, nonce="abc")
        # frozen dataclass raises FrozenInstanceError (subclass of AttributeError)
        with pytest.raises(AttributeError):
            d.decision = "deny"  # type: ignore[misc]
