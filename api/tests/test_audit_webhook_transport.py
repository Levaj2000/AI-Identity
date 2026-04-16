"""Tests for WebhookTransport — signing, HTTP behavior, error handling.

Uses respx to mock httpx calls so we never hit a real network.
"""

import hashlib
import hmac
import json

import httpx
import pytest

from common.audit.transports.webhook import (
    ENVELOPE_VERSION,
    WebhookTransport,
    _redact_error,
    _sign_body,
)

# ── Unit: body signing ───────────────────────────────────────────────


class TestBodySigning:
    def test_sign_body_matches_hmac_sha256(self):
        body = b'{"hello":"world"}'
        secret = "topsecret"
        sig = _sign_body(body, secret)
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_different_secret_different_sig(self):
        body = b"payload"
        assert _sign_body(body, "a") != _sign_body(body, "b")


# ── Unit: error redaction ────────────────────────────────────────────


class TestErrorRedaction:
    def test_urls_are_redacted(self):
        raw = "connect failed to https://secret.example.com/hook?token=xyz"
        clean = _redact_error(raw)
        assert "https://" not in clean
        assert "<url-redacted>" in clean

    def test_auth_tokens_redacted(self):
        raw = "401 Unauthorized Bearer abc123"
        clean = _redact_error(raw)
        assert "abc123" not in clean
        assert "<auth-redacted>" in clean

    def test_long_errors_truncated(self):
        raw = "x" * 2000
        clean = _redact_error(raw)
        assert len(clean) <= 501  # 500 cap + ellipsis


# ── Integration: deliver via mocked httpx ────────────────────────────


@pytest.fixture
def transport():
    return WebhookTransport(timeout_seconds=1.0)


def _capture_request(monkeypatch):
    """Wire httpx.Client.post to a capturing stub.

    Returns (captured_kwargs, set_response) tuple — capture_kwargs[-1] holds
    the last call, set_response assigns what the stub returns next.
    """
    captured: list[dict] = []
    response_box: dict[str, httpx.Response | Exception] = {}

    def fake_post(self, url, *, content=None, headers=None, **kwargs):  # noqa: ARG001
        captured.append({"url": url, "content": content, "headers": headers})
        item = response_box.get("r")
        if isinstance(item, Exception):
            raise item
        return item  # type: ignore[return-value]

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    def set_response(resp: httpx.Response | Exception) -> None:
        response_box["r"] = resp

    return captured, set_response


class TestWebhookDeliver:
    def test_2xx_counts_as_success(self, transport, monkeypatch):
        captured, set_response = _capture_request(monkeypatch)
        set_response(httpx.Response(202, text="ok"))

        result = transport.deliver(
            events=[{"id": 1}],
            url="https://hook.example.com/events",
            secret="shh",
        )

        assert result.success is True
        assert result.status_code == 202
        assert result.latency_ms is not None and result.latency_ms >= 0
        # Envelope shape check
        body_bytes = captured[-1]["content"]
        body = json.loads(body_bytes)
        assert body["version"] == ENVELOPE_VERSION
        assert body["events"] == [{"id": 1}]
        # Signature header matches body
        expected_sig = _sign_body(body_bytes, "shh")
        assert captured[-1]["headers"]["X-AI-Identity-Signature"] == expected_sig
        assert captured[-1]["headers"]["X-AI-Identity-Event-Count"] == "1"

    def test_5xx_counts_as_failure(self, transport, monkeypatch):
        _, set_response = _capture_request(monkeypatch)
        set_response(httpx.Response(503, text="upstream down"))

        result = transport.deliver(
            events=[{"id": 1}],
            url="https://hook.example.com/events",
            secret="shh",
        )

        assert result.success is False
        assert result.status_code == 503
        assert "503" in result.error

    def test_connection_error_redacted(self, transport, monkeypatch):
        _, set_response = _capture_request(monkeypatch)
        set_response(httpx.ConnectError("connect failed"))

        result = transport.deliver(
            events=[{"id": 1}],
            url="https://hook.example.com/hook?token=abc",
            secret="shh",
        )

        assert result.success is False
        # URL with token must not appear in the error
        assert "token=abc" not in (result.error or "")

    def test_rejects_http_url(self, transport):
        with pytest.raises(ValueError, match="https"):
            transport.deliver(
                events=[{"id": 1}],
                url="http://insecure.example.com/hook",
                secret="shh",
            )

    def test_rejects_empty_events(self, transport):
        with pytest.raises(ValueError, match="at least one event"):
            transport.deliver(events=[], url="https://x.co/h", secret="s")
