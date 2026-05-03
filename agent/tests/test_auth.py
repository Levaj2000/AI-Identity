"""Auth middleware + CORS lockdown for Ada's serve.py.

Surfaced by Insight #74 — serve.py had `allow_origins=["*"]` and zero auth,
so the only thing protecting Ada was the 127.0.0.1 bind. With these
changes:

- `ADA_REQUIRE_AUTH=1` → protected routes require a valid `X-Agent-Key`
  verified against AI Identity's `/api/v1/keys/verify`.
- CORS allowlist defaults to localhost-only; `ADA_ALLOWED_ORIGINS`
  overrides.

Tests use FastAPI's TestClient against a minimal app that wires in the
real middleware. `httpx.post` is patched so verify-key never hits the
network.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import auth as auth_mod
import pytest
from auth import VerifiedAgent, allowed_origins, auth_middleware, needs_auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Callable


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(auth_middleware)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"public": "yes"}

    @app.get("/version")
    def version() -> dict[str, str]:
        return {"sha": "test"}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/list-apps")
    def list_apps() -> list[str]:
        return ["ada"]

    @app.post("/run_sse")
    def run_sse() -> dict[str, str]:
        return {"ok": "ran"}

    @app.get("/apps/ada/users/u/sessions")
    def sessions() -> list[dict[str, str]]:
        return []

    return app


def _stub_verify_success(*args: Any, **kwargs: Any) -> object:  # noqa: ARG001
    class _R:
        status_code = 200

        @staticmethod
        def json() -> dict[str, Any]:
            return {
                "valid": True,
                "agent_id": "agt_abc",
                "agent_name": "ada",
                "metadata": {"role": "engineer"},
            }

    return _R()


def _stub_verify_invalid(*args: Any, **kwargs: Any) -> object:  # noqa: ARG001
    class _R:
        status_code = 200

        @staticmethod
        def json() -> dict[str, Any]:
            return {"valid": False, "reason": "key_revoked"}

    return _R()


@pytest.fixture
def auth_on(monkeypatch: pytest.MonkeyPatch) -> Callable[[], TestClient]:
    """Auth required + admin key configured."""
    monkeypatch.setenv("ADA_REQUIRE_AUTH", "1")
    monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "admin_test_key")
    return lambda: TestClient(_build_app())


@pytest.fixture
def auth_off(monkeypatch: pytest.MonkeyPatch) -> Callable[[], TestClient]:
    """Auth disabled (the default — preserves the launcher experience)."""
    monkeypatch.delenv("ADA_REQUIRE_AUTH", raising=False)
    monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "")
    return lambda: TestClient(_build_app())


class TestNeedsAuth:
    @pytest.mark.parametrize(
        "path",
        ["/", "/version", "/health", "/healthz", "/readyz", "/openapi.json", "/docs", "/redoc"],
    )
    def test_public_paths_skip_auth(self, path: str) -> None:
        assert needs_auth(path) is False

    @pytest.mark.parametrize(
        "path",
        ["/ui/", "/ui/index.html", "/ui/static/app.css"],
    )
    def test_ui_prefix_skips_auth(self, path: str) -> None:
        assert needs_auth(path) is False

    @pytest.mark.parametrize(
        "path",
        ["/list-apps", "/run_sse", "/apps/ada/users/u/sessions", "/run", "/something_new"],
    )
    def test_protected_paths_need_auth(self, path: str) -> None:
        # Default-deny: anything not on the public allowlist requires auth.
        assert needs_auth(path) is True


class TestAuthDisabled:
    def test_protected_route_open_when_auth_off(self, auth_off: Callable[[], TestClient]) -> None:
        client = auth_off()
        r = client.get("/list-apps")
        assert r.status_code == 200
        assert r.json() == ["ada"]

    def test_public_route_open(self, auth_off: Callable[[], TestClient]) -> None:
        client = auth_off()
        r = client.get("/version")
        assert r.status_code == 200


class TestAuthRequired:
    def test_missing_key_returns_401(self, auth_on: Callable[[], TestClient]) -> None:
        client = auth_on()
        r = client.get("/list-apps")
        assert r.status_code == 401
        assert "missing" in r.json()["error"].lower()

    def test_invalid_key_returns_401(self, auth_on: Callable[[], TestClient]) -> None:
        client = auth_on()
        with patch.object(auth_mod.httpx, "post", _stub_verify_invalid):
            r = client.get("/list-apps", headers={"X-Agent-Key": "bad_key"})
        assert r.status_code == 401
        assert "invalid" in r.json()["error"].lower()

    def test_valid_key_returns_200(self, auth_on: Callable[[], TestClient]) -> None:
        client = auth_on()
        with patch.object(auth_mod.httpx, "post", _stub_verify_success):
            r = client.get("/list-apps", headers={"X-Agent-Key": "good_key"})
        assert r.status_code == 200
        assert r.json() == ["ada"]

    def test_public_route_open_even_with_auth_required(
        self, auth_on: Callable[[], TestClient]
    ) -> None:
        client = auth_on()
        for path in ("/", "/version", "/healthz"):
            r = client.get(path)
            assert r.status_code == 200, f"{path} should be public"

    def test_post_route_protected(self, auth_on: Callable[[], TestClient]) -> None:
        client = auth_on()
        r = client.post("/run_sse")
        assert r.status_code == 401

    def test_admin_key_missing_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Auth required but admin credential not configured — refuse, not allow.
        monkeypatch.setenv("ADA_REQUIRE_AUTH", "1")
        monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "")
        client = TestClient(_build_app())
        r = client.get("/list-apps", headers={"X-Agent-Key": "anything"})
        assert r.status_code == 503
        assert "ADA_ADMIN_KEY" in r.json()["error"] or "admin" in r.json()["error"].lower()


class TestVerifyAgentKey:
    def test_returns_none_when_no_admin_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "")
        assert auth_mod.verify_agent_key("any_key") is None

    def test_returns_none_when_empty_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "admin_key")
        assert auth_mod.verify_agent_key("") is None

    def test_returns_verified_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "admin_key")
        with patch.object(auth_mod.httpx, "post", _stub_verify_success):
            result = auth_mod.verify_agent_key("user_key")
        assert isinstance(result, VerifiedAgent)
        assert result.agent_id == "agt_abc"
        assert result.role == "engineer"

    def test_returns_none_on_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(auth_mod, "ADA_ADMIN_KEY", "admin_key")
        with patch.object(auth_mod.httpx, "post", _stub_verify_invalid):
            result = auth_mod.verify_agent_key("revoked_key")
        assert result is None


class TestAllowedOrigins:
    def test_default_is_localhost_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ADA_ALLOWED_ORIGINS", raising=False)
        origins = allowed_origins()
        assert "http://localhost:8000" in origins
        assert "http://127.0.0.1:8000" in origins
        assert "*" not in origins

    def test_custom_origins_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "ADA_ALLOWED_ORIGINS", "https://ada.example.com, https://internal.example.com"
        )
        assert allowed_origins() == ["https://ada.example.com", "https://internal.example.com"]


class TestCORSPreflight:
    def test_disallowed_origin_no_cors_headers(
        self, auth_off: Callable[[], TestClient], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Default allowlist is localhost-only — a preflight from evil.com must not
        # receive CORS headers, which is what blocks the browser.
        monkeypatch.delenv("ADA_ALLOWED_ORIGINS", raising=False)
        client = auth_off()
        r = client.options(
            "/list-apps",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette returns 400 for a CORSMiddleware-rejected preflight; either
        # way, the disallowed origin must NOT be echoed in the CORS header.
        assert r.headers.get("access-control-allow-origin") != "https://evil.example.com"

    def test_allowed_origin_gets_cors_headers(self, auth_off: Callable[[], TestClient]) -> None:
        client = auth_off()
        r = client.options(
            "/list-apps",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.headers.get("access-control-allow-origin") == "http://localhost:8000"
