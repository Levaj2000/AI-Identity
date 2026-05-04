"""Tests for the ``aid`` CLI.

Mocks ``httpx.Client`` so tests never hit the network. Validates the
duration parser, agent resolution (by UUID and by name with happy /
not-found / ambiguous cases), the table renderer, and the end-to-end
``aid audit`` invocation including ``--verify-chain``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import aid
import httpx
import pytest


def _resp(status: int, body: Any) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.json.return_value = body
    r.raise_for_status = MagicMock()
    if status >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=r
        )
    return r


@pytest.fixture
def admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_IDENTITY_ADMIN_KEY", "aid_admin_test")
    monkeypatch.setenv("AI_IDENTITY_API_URL", "https://api.test")


class TestParseDuration:
    @pytest.mark.parametrize(
        ("spec", "expected"),
        [
            ("7d", timedelta(days=7)),
            ("24h", timedelta(hours=24)),
            ("30m", timedelta(minutes=30)),
            ("90s", timedelta(seconds=90)),
            ("1d", timedelta(days=1)),
        ],
    )
    def test_valid(self, spec: str, expected: timedelta) -> None:
        assert aid.parse_duration(spec) == expected

    @pytest.mark.parametrize(
        "spec",
        ["", "abc", "7days", "1.5d", "-3h", "10w", "h7"],
    )
    def test_invalid_raises(self, spec: str) -> None:
        with pytest.raises(ValueError, match="invalid duration"):
            aid.parse_duration(spec)


class TestResolveAgent:
    def test_uuid_lookup(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        uuid = "11111111-2222-3333-4444-555555555555"
        client.get.return_value = _resp(200, {"id": uuid, "name": "ada"})

        agent_id, name = aid.resolve_agent(client, uuid)
        assert agent_id == uuid
        assert name == "ada"
        client.get.assert_called_once()
        called_url = client.get.call_args[0][0]
        assert f"/api/v1/agents/{uuid}" in called_url

    def test_uuid_not_found_exits(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(404, {})
        with pytest.raises(SystemExit) as exc:
            aid.resolve_agent(client, "11111111-2222-3333-4444-555555555555")
        assert exc.value.code == 2

    def test_name_lookup_single_match(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "abc", "name": "cto"},
                {"id": "def", "name": "cto-deprecated"},  # name doesn't match exactly
            ],
        )
        agent_id, name = aid.resolve_agent(client, "cto")
        assert agent_id == "abc"
        assert name == "cto"

    def test_name_no_match_exits(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(200, [])
        with pytest.raises(SystemExit) as exc:
            aid.resolve_agent(client, "nonexistent")
        assert exc.value.code == 2

    def test_name_ambiguous_exits(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "abc", "name": "cto"},
                {"id": "def", "name": "cto"},
            ],
        )
        with pytest.raises(SystemExit) as exc:
            aid.resolve_agent(client, "cto")
        assert exc.value.code == 2

    def test_persona_alias_resolves_to_canonical_name(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``--agent cto`` should resolve to the registered agent ``cto-agent``."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "abc", "name": "cto-agent"},
                {"id": "def", "name": "ada"},
            ],
        )
        agent_id, name = aid.resolve_agent(client, "cto")
        assert agent_id == "abc"
        assert name == "cto-agent"
        # Note printed to stderr so the alias is visible
        err = capsys.readouterr().err
        assert "'cto'" in err and "'cto-agent'" in err

    def test_generic_hyphen_agent_fallback(self, admin_key: None) -> None:  # noqa: ARG002
        """Non-aliased name ``foo`` should still try ``foo-agent`` before erroring."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [{"id": "xyz", "name": "foo-agent"}],
        )
        agent_id, name = aid.resolve_agent(client, "foo")
        assert agent_id == "xyz"
        assert name == "foo-agent"

    def test_exact_match_preferred_over_alias(self, admin_key: None) -> None:  # noqa: ARG002
        """If both ``cto`` and ``cto-agent`` exist, the exact match wins."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "exact", "name": "cto"},
                {"id": "alias", "name": "cto-agent"},
            ],
        )
        agent_id, _ = aid.resolve_agent(client, "cto")
        assert agent_id == "exact"

    def test_unknown_name_lists_known_agents_in_error(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "1", "name": "ada"},
                {"id": "2", "name": "cto-agent"},
            ],
        )
        with pytest.raises(SystemExit) as exc:
            aid.resolve_agent(client, "nonexistent")
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "ada" in err
        assert "cto-agent" in err


class TestFetchAuditEntries:
    def test_returns_list_directly(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(200, [{"timestamp": "t1"}, {"timestamp": "t2"}])
        result = aid.fetch_audit_entries(client, "abc", timedelta(days=7), 50)
        assert len(result) == 2

    def test_returns_items_envelope(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(200, {"items": [{"timestamp": "t1"}]})
        result = aid.fetch_audit_entries(client, "abc", timedelta(days=1), 50)
        assert len(result) == 1

    def test_caps_limit_at_500(self, admin_key: None) -> None:  # noqa: ARG002
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(200, [])
        aid.fetch_audit_entries(client, "abc", timedelta(days=1), 9999)
        kwargs = client.get.call_args[1]
        assert kwargs["params"]["limit"] == 500


class TestRenderTable:
    def test_empty(self) -> None:
        assert "No audit entries" in aid.render_table([])

    def test_includes_header_and_row(self) -> None:
        out = aid.render_table(
            [
                {
                    "timestamp": "2026-05-06T10:00:00Z",
                    "decision": "allowed",
                    "method": "POST",
                    "endpoint": "/api/v1/briefings",
                    "correlation_id": "corr-abc",
                }
            ]
        )
        assert "TIMESTAMP" in out
        assert "DECISION" in out
        assert "/api/v1/briefings" in out
        assert "allowed" in out

    def test_long_endpoint_truncated_with_ellipsis(self) -> None:
        long_endpoint = "/api/v1/" + ("x" * 100)
        out = aid.render_table([{"endpoint": long_endpoint, "decision": "allowed"}])
        assert "…" in out
        assert long_endpoint not in out


class TestCmdAuditEndToEnd:
    def test_audit_happy_path(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            # 1) name → agent record
            # 2) audit entries
            client.get.side_effect = [
                _resp(200, [{"id": "abc", "name": "cto"}]),
                _resp(
                    200,
                    [
                        {
                            "timestamp": "2026-05-06T10:00:00Z",
                            "decision": "allowed",
                            "method": "POST",
                            "endpoint": "/api/v1/briefings",
                            "correlation_id": "c1",
                        }
                    ],
                ),
            ]

            exit_code = aid.main(["audit", "--agent", "cto", "--since", "24h"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "Agent: cto" in out
        assert "/api/v1/briefings" in out

    def test_audit_with_verify_chain(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.side_effect = [
                _resp(200, [{"id": "abc", "name": "cto"}]),
                _resp(200, {"valid": True, "total_entries": 17, "entries_verified": 17}),
                _resp(200, []),
            ]

            exit_code = aid.main(["audit", "--agent", "cto", "--verify-chain"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "VALID" in out
        assert "17" in out

    def test_audit_with_invalid_chain_reports_break(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.side_effect = [
                _resp(200, [{"id": "abc", "name": "cto"}]),
                _resp(
                    200,
                    {
                        "valid": False,
                        "total_entries": 17,
                        "entries_verified": 11,
                        "first_break": "entry 12 hash mismatch",
                    },
                ),
                _resp(200, []),
            ]

            exit_code = aid.main(["audit", "--agent", "cto", "--verify-chain"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "INVALID" in out
        assert "entry 12 hash mismatch" in out

    def test_missing_admin_key_exits(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.delenv("AI_IDENTITY_ADMIN_KEY", raising=False)
        with pytest.raises(SystemExit) as exc:
            aid.main(["audit", "--agent", "cto"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "AI_IDENTITY_ADMIN_KEY" in err
        # Improved guidance — surfaces the email-as-key auth path explicitly
        assert "email" in err.lower()


class TestCmdAgents:
    def test_lists_agents_sorted(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.return_value = _resp(
                200,
                [
                    {"id": "z-id", "name": "zebra-agent"},
                    {"id": "a-id", "name": "ada"},
                    {"id": "c-id", "name": "cto-agent"},
                ],
            )
            exit_code = aid.main(["agents"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "NAME" in out and "AGENT_ID" in out
        # Sorted: ada, cto-agent, zebra-agent
        ada_pos = out.index("ada")
        cto_pos = out.index("cto-agent")
        zebra_pos = out.index("zebra-agent")
        assert ada_pos < cto_pos < zebra_pos
        assert "a-id" in out and "c-id" in out and "z-id" in out

    def test_empty_agent_list(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.return_value = _resp(200, [])
            exit_code = aid.main(["agents"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "No agents" in out


class TestArgparse:
    def test_audit_requires_agent(self) -> None:
        parser = aid.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["audit"])

    def test_default_since(self) -> None:
        parser = aid.build_parser()
        args = parser.parse_args(["audit", "--agent", "cto"])
        assert args.since == "7d"
        assert args.limit == 50
        assert args.verify_chain is False

    def test_no_subcommand_errors(self) -> None:
        parser = aid.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])
