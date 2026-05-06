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

    def test_name_collision_skips_revoked_when_one_active(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Two ceo-agents (one active, one revoked) → resolve to active one with stderr note."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "active-id", "name": "ceo-agent", "status": "active"},
                {"id": "revoked-id", "name": "ceo-agent", "status": "revoked"},
            ],
        )
        agent_id, name = aid.resolve_agent(client, "ceo-agent")
        assert agent_id == "active-id"
        assert name == "ceo-agent"
        err = capsys.readouterr().err
        assert "1 revoked" in err
        assert "active-id" in err

    def test_name_collision_via_alias_skips_revoked(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Alias resolution should also skip revoked siblings (`ceo` → `ceo-agent`)."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "active-id", "name": "ceo-agent", "status": "active"},
                {"id": "revoked-id", "name": "ceo-agent", "status": "revoked"},
            ],
        )
        agent_id, _ = aid.resolve_agent(client, "ceo")
        assert agent_id == "active-id"
        err = capsys.readouterr().err
        # Both the alias note AND the revoked-skipped note should appear
        assert "'ceo'" in err and "'ceo-agent'" in err
        assert "1 revoked" in err

    def test_name_collision_all_revoked_errors(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """If every name match is revoked, error with a clear message pointing to UUID."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "r1", "name": "ceo-agent", "status": "revoked"},
                {"id": "r2", "name": "ceo-agent", "status": "revoked"},
            ],
        )
        with pytest.raises(SystemExit) as exc:
            aid.resolve_agent(client, "ceo-agent")
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "all 2 agents" in err and "revoked" in err

    def test_name_collision_multiple_active_still_errors(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """If two active agents share a name, can't auto-pick — error and ask for UUID."""
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = _resp(
            200,
            [
                {"id": "a1", "name": "ceo-agent", "status": "active"},
                {"id": "a2", "name": "ceo-agent", "status": "active"},
                {"id": "r1", "name": "ceo-agent", "status": "revoked"},
            ],
        )
        with pytest.raises(SystemExit) as exc:
            aid.resolve_agent(client, "ceo-agent")
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "multiple active agents" in err
        assert "(2 matches)" in err

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

    def test_includes_header_and_row_normalizes_decision(self) -> None:
        """Legacy `allowed` should display-normalize to `allow` (#351)."""
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
        # Normalized form, not the legacy past-tense
        assert "allow " in out  # column-padded; "allow" alone could match "allowed"
        assert "allowed" not in out

    def test_long_endpoint_truncated_with_ellipsis_default(self) -> None:
        long_endpoint = "/api/v1/" + ("x" * 100)
        out = aid.render_table([{"endpoint": long_endpoint, "decision": "allowed"}])
        assert "…" in out
        assert long_endpoint not in out

    def test_wide_disables_truncation(self) -> None:
        """`wide=True` should auto-size columns and show full endpoint paths (#352)."""
        long_endpoint = "/api/v1/agents/" + "x" * 60
        out = aid.render_table([{"endpoint": long_endpoint, "decision": "allow"}], wide=True)
        assert "…" not in out
        assert long_endpoint in out

    def test_decision_normalization_denied_to_deny(self) -> None:
        out = aid.render_table([{"decision": "denied", "endpoint": "/x"}])
        assert "deny " in out
        assert "denied" not in out

    def test_unknown_decision_passes_through(self) -> None:
        """Don't silently rewrite unknown decision strings."""
        out = aid.render_table([{"decision": "throttled", "endpoint": "/x"}])
        assert "throttled" in out


class TestNormalizeDecision:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("allowed", "allow"),
            ("denied", "deny"),
            ("allow", "allow"),
            ("deny", "deny"),
            ("throttled", "throttled"),
            ("", ""),
        ],
    )
    def test_mapping(self, raw: str, expected: str) -> None:
        assert aid._normalize_decision(raw) == expected

    def test_non_string_returns_empty(self) -> None:
        assert aid._normalize_decision(None) == ""
        assert aid._normalize_decision(123) == ""


class TestFilterByDecision:
    def test_filter_allow_matches_legacy_allowed(self) -> None:
        entries = [
            {"decision": "allow", "id": 1},
            {"decision": "allowed", "id": 2},
            {"decision": "deny", "id": 3},
        ]
        out = aid.filter_by_decision(entries, "allow")
        assert [e["id"] for e in out] == [1, 2]

    def test_filter_deny_matches_legacy_denied(self) -> None:
        entries = [
            {"decision": "deny", "id": 1},
            {"decision": "denied", "id": 2},
            {"decision": "allow", "id": 3},
        ]
        out = aid.filter_by_decision(entries, "deny")
        assert [e["id"] for e in out] == [1, 2]

    def test_filter_empty_input(self) -> None:
        assert aid.filter_by_decision([], "allow") == []


class TestSummarizeAndRender:
    def test_summarize_counts_and_range(self) -> None:
        entries = [
            {"decision": "allow", "timestamp": "2026-05-04T10:00:00Z"},
            {"decision": "allowed", "timestamp": "2026-05-05T10:00:00Z"},
            {"decision": "deny", "timestamp": "2026-05-06T10:00:00Z"},
            {"decision": "throttled", "timestamp": "2026-05-06T11:00:00Z"},
        ]
        s = aid.summarize_entries(entries)
        assert s["total"] == 4
        assert s["allow"] == 2
        assert s["deny"] == 1
        assert s["other"] == 1
        assert s["earliest"] == "2026-05-04"
        assert s["latest"] == "2026-05-06"

    def test_summarize_empty(self) -> None:
        s = aid.summarize_entries([])
        assert s["total"] == 0 and s["allow"] == 0 and s["deny"] == 0
        assert s["earliest"] is None and s["latest"] is None

    def test_render_summary_line_range(self) -> None:
        s = {
            "total": 20,
            "allow": 19,
            "deny": 1,
            "other": 0,
            "earliest": "2026-04-25",
            "latest": "2026-05-04",
        }
        line = aid.render_summary_line(s)
        assert line == "20 entries: 19 allow, 1 deny | 2026-04-25..2026-05-04"

    def test_render_summary_line_single_day(self) -> None:
        s = {
            "total": 5,
            "allow": 5,
            "deny": 0,
            "other": 0,
            "earliest": "2026-05-06",
            "latest": "2026-05-06",
        }
        line = aid.render_summary_line(s)
        assert line == "5 entries: 5 allow, 0 deny | 2026-05-06"

    def test_render_summary_line_includes_other_count_when_nonzero(self) -> None:
        s = {
            "total": 3,
            "allow": 1,
            "deny": 1,
            "other": 1,
            "earliest": None,
            "latest": None,
        }
        line = aid.render_summary_line(s)
        assert "1 other" in line


class TestRenderByDay:
    def test_groups_by_date_sorted_newest_first(self) -> None:
        entries = [
            {"decision": "allow", "timestamp": "2026-05-04T10:00:00Z"},
            {"decision": "allow", "timestamp": "2026-05-04T11:00:00Z"},
            {"decision": "deny", "timestamp": "2026-05-04T12:00:00Z"},
            {"decision": "allow", "timestamp": "2026-05-06T10:00:00Z"},
        ]
        out = aid.render_by_day(entries)
        assert "DATE" in out and "TOTAL" in out and "ALLOW" in out and "DENY" in out
        # Newest first
        idx_06 = out.index("2026-05-06")
        idx_04 = out.index("2026-05-04")
        assert idx_06 < idx_04
        # Day with 3 entries, 2 allow, 1 deny
        line_04 = next(line for line in out.splitlines() if line.startswith("2026-05-04"))
        cells = line_04.split()
        assert cells[1] == "3" and cells[2] == "2" and cells[3] == "1"

    def test_empty_input(self) -> None:
        assert "No audit entries" in aid.render_by_day([])


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

    def test_default_hides_revoked_with_footer(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Default `aid agents` filters out non-active agents and prints a footer."""
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.return_value = _resp(
                200,
                [
                    {"id": "ada-id", "name": "ada", "status": "active"},
                    {"id": "r1-id", "name": "demo-1", "status": "revoked"},
                    {"id": "r2-id", "name": "demo-2", "status": "revoked"},
                    {"id": "cto-id", "name": "cto-agent", "status": "active"},
                ],
            )
            exit_code = aid.main(["agents"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "ada" in out and "cto-agent" in out
        assert "demo-1" not in out
        assert "demo-2" not in out
        assert "2 non-active agent(s) hidden" in out
        assert "--all" in out

    def test_all_flag_shows_revoked_with_status_suffix(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`aid agents --all` includes revoked agents annotated with `(revoked)`."""
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.return_value = _resp(
                200,
                [
                    {"id": "a1", "name": "ada", "status": "active"},
                    {"id": "r1", "name": "demo-1", "status": "revoked"},
                ],
            )
            exit_code = aid.main(["agents", "--all"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "ada" in out
        assert "demo-1 (revoked)" in out
        # Footer should NOT appear when --all is set
        assert "hidden" not in out

    def test_default_no_footer_when_no_hidden(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """No footer noise when every agent is active."""
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        with patch.object(aid.httpx, "Client", return_value=client):
            client.get.return_value = _resp(
                200,
                [
                    {"id": "a1", "name": "ada", "status": "active"},
                    {"id": "c1", "name": "cto-agent", "status": "active"},
                ],
            )
            exit_code = aid.main(["agents"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "hidden" not in out


class TestCmdAuditNewFlags:
    """End-to-end tests for `aid audit` flags added in #351 + #352."""

    @staticmethod
    def _mock_client_with_entries(
        entries: list[dict[str, Any]],
    ) -> tuple[Any, Any]:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        client.get.side_effect = [
            _resp(200, [{"id": "abc", "name": "cto"}]),
            _resp(200, entries),
        ]
        patcher = patch.object(aid.httpx, "Client", return_value=client)
        return client, patcher

    def test_header_includes_summary_counts(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Default audit output's header line carries the summary even without --summary."""
        entries = [
            {"decision": "allow", "timestamp": "2026-05-06T10:00:00Z"},
            {"decision": "denied", "timestamp": "2026-05-06T11:00:00Z"},
        ]
        _, patcher = self._mock_client_with_entries(entries)
        with patcher:
            exit_code = aid.main(["audit", "--agent", "cto"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "2 entries:" in out
        assert "1 allow" in out and "1 deny" in out

    def test_decision_filter_keeps_only_matching(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        entries = [
            {
                "decision": "allow",
                "timestamp": "2026-05-06T10:00:00Z",
                "endpoint": "/keep",
            },
            {
                "decision": "deny",
                "timestamp": "2026-05-06T11:00:00Z",
                "endpoint": "/drop",
            },
        ]
        _, patcher = self._mock_client_with_entries(entries)
        with patcher:
            exit_code = aid.main(["audit", "--agent", "cto", "--decision", "allow"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "/keep" in out
        assert "/drop" not in out
        assert "filtered from 2 fetched" in out

    def test_decision_filter_matches_legacy_form(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`--decision allow` should also match historical `allowed` rows."""
        entries = [
            {
                "decision": "allowed",
                "timestamp": "2026-04-25T20:21:53Z",
                "endpoint": "/api/v1/agents",
            },
            {
                "decision": "deny",
                "timestamp": "2026-05-06T11:00:00Z",
                "endpoint": "/x",
            },
        ]
        _, patcher = self._mock_client_with_entries(entries)
        with patcher:
            aid.main(["audit", "--agent", "cto", "--decision", "allow"])
        out = capsys.readouterr().out
        assert "/api/v1/agents" in out
        assert "/x" not in out

    def test_summary_flag_suppresses_detail_table(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        entries = [
            {
                "decision": "allow",
                "timestamp": "2026-05-06T10:00:00Z",
                "endpoint": "/x",
            },
        ]
        _, patcher = self._mock_client_with_entries(entries)
        with patcher:
            aid.main(["audit", "--agent", "cto", "--summary"])
        out = capsys.readouterr().out
        assert "1 entries:" in out
        assert "TIMESTAMP" not in out
        assert "/x" not in out

    def test_by_day_replaces_detail_table_with_rollup(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        entries = [
            {
                "decision": "allow",
                "timestamp": "2026-05-04T10:00:00Z",
                "endpoint": "/x",
            },
            {
                "decision": "deny",
                "timestamp": "2026-05-04T11:00:00Z",
                "endpoint": "/y",
            },
            {
                "decision": "allow",
                "timestamp": "2026-05-06T10:00:00Z",
                "endpoint": "/z",
            },
        ]
        _, patcher = self._mock_client_with_entries(entries)
        with patcher:
            aid.main(["audit", "--agent", "cto", "--by-day"])
        out = capsys.readouterr().out
        assert "DATE" in out and "ALLOW" in out and "DENY" in out
        assert "2026-05-04" in out and "2026-05-06" in out
        # Detail rows suppressed
        assert "/x" not in out and "/y" not in out and "/z" not in out

    def test_wide_disables_truncation_in_audit_output(
        self,
        admin_key: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        long_endpoint = "/api/v1/agents/" + "u" * 60
        entries = [
            {
                "decision": "allow",
                "timestamp": "2026-05-06T10:00:00Z",
                "endpoint": long_endpoint,
            },
        ]
        _, patcher = self._mock_client_with_entries(entries)
        with patcher:
            aid.main(["audit", "--agent", "cto", "--wide"])
        out = capsys.readouterr().out
        assert long_endpoint in out
        assert "…" not in out


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
        assert args.decision is None
        assert args.wide is False
        assert args.summary is False
        assert args.by_day is False

    def test_audit_decision_flag_validated(self) -> None:
        parser = aid.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["audit", "--agent", "cto", "--decision", "maybe"])

    def test_no_subcommand_errors(self) -> None:
        parser = aid.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])
