#!/usr/bin/env python3
"""aid — AI Identity audit review CLI.

Minimal command-line tool for reviewing an agent's audit trail. Hits the
AI Identity API and prints a table of audit entries plus an optional
chain-integrity check.

Sprint 12 carryover (#330). Pairs with the existing offline-verification
tool in this directory (``ai_identity_verify.py``) — that one verifies a
forensic export without any network access. This one reaches the live API
for day-to-day "what did persona X do this week?" review.

Authentication:

    The dev-admin auth path today is the legacy email-as-key fallback —
    set ``AI_IDENTITY_ADMIN_KEY`` to your AI Identity account email. This
    is the same value the dashboard accepts in the ``X-API-Key`` header.
    A first-class developer-key flow is on the roadmap; until then this
    is the path that works.

Usage:

    export AI_IDENTITY_ADMIN_KEY="$YOUR_EMAIL"
    python cli/aid.py agents                              # list agents
    python cli/aid.py audit --agent cto --since 7d        # alias OK
    python cli/aid.py audit --agent cto-agent --since 7d  # exact name OK
    python cli/aid.py audit --agent <UUID> --since 24h --verify-chain
    python cli/aid.py audit --agent cto --since 7d --limit 200

Persona name aliases:

    Skill-style names like ``cto``, ``pm``, ``marketing``, ``security``,
    ``sales``, ``ceo`` resolve to the registered agents
    ``cto-agent``, ``pm-agent``, etc. ``ada`` and ``webhook-receiver``
    have no suffix and are used verbatim. Use ``aid agents`` to see the
    canonical names.

Note: webhook-driven briefings appear under the ``webhook-receiver`` agent
by design — see Insight #71.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_API_URL = "https://api.ai-identity.co"
HTTP_TIMEOUT_S = 15.0

_DURATION_RE = re.compile(r"^(\d+)([smhd])$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def parse_duration(spec: str) -> timedelta:
    """Parse durations like ``7d``, ``24h``, ``30m``, ``90s``."""
    m = _DURATION_RE.match(spec.strip())
    if not m:
        raise ValueError(f"invalid duration {spec!r}; use formats like 7d, 24h, 30m, 90s")
    n, unit = int(m.group(1)), m.group(2)
    return {
        "s": timedelta(seconds=n),
        "m": timedelta(minutes=n),
        "h": timedelta(hours=n),
        "d": timedelta(days=n),
    }[unit]


def _api_url() -> str:
    return os.environ.get("AI_IDENTITY_API_URL", DEFAULT_API_URL).rstrip("/")


def _admin_key() -> str:
    key = os.environ.get("AI_IDENTITY_ADMIN_KEY", "")
    if not key:
        print(
            "ERROR: AI_IDENTITY_ADMIN_KEY is not set.\n"
            "       Set it to your AI Identity account email — that's the legacy\n"
            '       email-as-key auth the API accepts (e.g. export AI_IDENTITY_ADMIN_KEY="you@example.com").\n'
            "       See cli/README.md for the bootstrap walkthrough.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return key


# Skill-style names → canonical agent registry names. Lets `aid audit --agent cto`
# resolve to the registered agent `cto-agent`. Single source of truth so
# resolve_agent() and cmd_agents() stay in sync.
PERSONA_ALIASES: dict[str, str] = {
    "ceo": "ceo-agent",
    "cto": "cto-agent",
    "pm": "pm-agent",
    "security": "security-agent",
    "marketing": "marketing-agent",
    "sales": "sales-agent",
}


def resolve_agent(client: httpx.Client, agent: str) -> tuple[str, str]:
    """Return ``(agent_id, agent_name)``. Accepts a UUID, a canonical name, or a persona alias.

    Persona aliases (``cto`` → ``cto-agent``, etc.) are resolved against
    :data:`PERSONA_ALIASES` so users can type the skill-style name they
    already know. Falls back to a generic ``<name>-agent`` retry for
    aliases not in the table.

    Raises :class:`SystemExit` (exit code 2) when ambiguous or not found,
    so callers don't need to wrap; the CLI surfaces a clear message.
    """
    headers = {"X-API-Key": _admin_key()}

    if _UUID_RE.match(agent):
        resp = client.get(f"{_api_url()}/api/v1/agents/{agent}", headers=headers)
        if resp.status_code == 404:
            print(f"ERROR: no agent with id {agent}", file=sys.stderr)
            raise SystemExit(2)
        resp.raise_for_status()
        body = resp.json()
        return body["id"], body.get("name", "")

    # Build the candidate list from the input itself, then known aliases,
    # then a generic "-agent" fallback. First exact match wins. Order
    # matters: prefer an exact name match over an alias of the same word.
    candidates: list[str] = [agent]
    if agent in PERSONA_ALIASES:
        candidates.append(PERSONA_ALIASES[agent])
    elif not agent.endswith("-agent"):
        candidates.append(f"{agent}-agent")

    resp = client.get(
        f"{_api_url()}/api/v1/agents",
        headers=headers,
        params={"limit": 100},
    )
    resp.raise_for_status()
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("agents", []))

    for candidate in candidates:
        matches = [a for a in items if a.get("name") == candidate]
        if len(matches) == 1:
            if candidate != agent:
                print(f"note: resolved {agent!r} → {candidate!r}", file=sys.stderr)
            return matches[0]["id"], matches[0]["name"]
        if len(matches) > 1:
            # Name collision. Prefer agents with status == "active" (or no
            # status field, for backward compat / test fixtures). If exactly
            # one active agent remains after filtering revoked siblings,
            # use it and tell the user what was skipped.
            active = [m for m in matches if m.get("status", "active") == "active"]
            if len(active) == 1:
                if candidate != agent:
                    print(f"note: resolved {agent!r} → {candidate!r}", file=sys.stderr)
                skipped = len(matches) - 1
                print(
                    f"note: {skipped} revoked agent(s) named {candidate!r} "
                    f"skipped; using active one ({active[0]['id']})",
                    file=sys.stderr,
                )
                return active[0]["id"], active[0]["name"]
            if not active:
                print(
                    f"ERROR: all {len(matches)} agents named {candidate!r} are "
                    "revoked. Use the UUID of the specific agent you want to query.",
                    file=sys.stderr,
                )
                raise SystemExit(2)
            print(
                f"ERROR: multiple active agents named {candidate!r} "
                f"({len(active)} matches); use the UUID instead",
                file=sys.stderr,
            )
            raise SystemExit(2)

    # Nothing matched any candidate — emit a useful error with known names.
    known = sorted({str(a.get("name", "")) for a in items if a.get("name")})
    print(f"ERROR: no agent found with name {agent!r}", file=sys.stderr)
    if known:
        preview = ", ".join(known[:10])
        suffix = f" (and {len(known) - 10} more — run `aid agents`)" if len(known) > 10 else ""
        print(f"       known agents: {preview}{suffix}", file=sys.stderr)
    raise SystemExit(2)


def fetch_audit_entries(
    client: httpx.Client,
    agent_id: str,
    since: timedelta,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch audit log entries for ``agent_id`` from now-``since`` through now.

    The path intentionally has NO trailing slash — the API is currently
    deployed behind a proxy that doesn't forward X-Forwarded-Proto, so
    FastAPI's auto-generated trailing-slash 307 redirect emits an
    ``http://`` location and httpx (correctly) refuses to follow the
    cross-protocol downgrade. Tracked as Sprint 13 #342.
    """
    start = (datetime.now(timezone.utc) - since).isoformat()
    params = {"agent_id": agent_id, "start_date": start, "limit": min(limit, 500)}
    resp = client.get(
        f"{_api_url()}/api/v1/audit",
        headers={"X-API-Key": _admin_key()},
        params=params,
    )
    resp.raise_for_status()
    body = resp.json()
    if isinstance(body, list):
        return body
    return body.get("items", body.get("entries", []))


def verify_chain(client: httpx.Client, agent_id: str) -> dict[str, Any]:
    """Call the chain-integrity verifier scoped to ``agent_id``."""
    resp = client.get(
        f"{_api_url()}/api/v1/audit/verify",
        headers={"X-API-Key": _admin_key()},
        params={"agent_id": agent_id},
    )
    resp.raise_for_status()
    return resp.json()


# Each column: (display_label, fallback lookup keys, width). Multiple keys
# let the timestamp column accept either ``timestamp`` (legacy / test fixtures)
# or ``created_at`` (what the live API actually returns).
_TABLE_COLS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("TIMESTAMP", ("timestamp", "created_at"), 25),
    ("DECISION", ("decision",), 9),
    ("METHOD", ("method",), 6),
    ("ENDPOINT", ("endpoint",), 50),
    ("CORRELATION_ID", ("correlation_id",), 16),
)


# Decision form normalization. Server-side normalization landed in PR #235
# but historical entries written before that still carry the legacy past-
# tense form. We display-normalize so the founder/auditor sees one
# consistent vocabulary regardless of when the row was written.
_DECISION_ALIASES: dict[str, str] = {"allowed": "allow", "denied": "deny"}


def _normalize_decision(value: Any) -> str:
    """Map legacy past-tense decision values onto the canonical form.

    ``"allowed"`` → ``"allow"``, ``"denied"`` → ``"deny"``. Other values
    pass through unchanged. Non-string input returns ``""``.
    """
    if not isinstance(value, str):
        return ""
    return _DECISION_ALIASES.get(value, value)


def _entry_field(entry: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first non-empty value for any of ``keys`` on ``entry``."""
    for key in keys:
        candidate = entry.get(key)
        if candidate not in (None, ""):
            return candidate
    return ""


def render_table(entries: list[dict[str, Any]], *, wide: bool = False) -> str:
    """Plain-text table — no color, no Unicode beyond `─`. Stays portable.

    When ``wide`` is True, columns auto-size to the widest content instead
    of truncating with an ellipsis. Useful when an endpoint path includes
    a UUID and the default 50-char column would hide it.
    """
    if not entries:
        return "No audit entries in the requested window."

    # Resolve display value once per (entry, column) so width calc and
    # row render agree. Decision column gets normalized for display.
    rows_text: list[list[str]] = []
    for entry in entries:
        row: list[str] = []
        for label, keys, _w in _TABLE_COLS:
            val = _entry_field(entry, keys)
            if label == "DECISION":
                val = _normalize_decision(val)
            row.append(str(val))
        rows_text.append(row)

    if wide:
        widths = [
            max(len(label), max(len(r[i]) for r in rows_text))
            for i, (label, _, _) in enumerate(_TABLE_COLS)
        ]
    else:
        widths = [w for _, _, w in _TABLE_COLS]

    header = "  ".join(_TABLE_COLS[i][0].ljust(widths[i]) for i in range(len(_TABLE_COLS)))
    sep = "  ".join("-" * widths[i] for i in range(len(_TABLE_COLS)))
    lines = [header, sep]
    for row in rows_text:
        cells: list[str] = []
        for i, text in enumerate(row):
            width = widths[i]
            if not wide and len(text) > width:
                text = text[: width - 1] + "…"
            cells.append(text.ljust(width))
        lines.append("  ".join(cells))
    return "\n".join(lines)


def filter_by_decision(entries: list[dict[str, Any]], decision: str) -> list[dict[str, Any]]:
    """Keep only entries whose normalized decision equals ``decision``.

    Pre-applies :func:`_normalize_decision` so callers can pass ``"allow"``
    and still match the legacy ``"allowed"`` form.
    """
    target = _normalize_decision(decision)
    return [e for e in entries if _normalize_decision(e.get("decision")) == target]


def summarize_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute counts + timestamp range for ``entries``. Empty input → zeros."""
    counts: dict[str, int] = {"allow": 0, "deny": 0, "other": 0}
    timestamps: list[str] = []
    for e in entries:
        d = _normalize_decision(e.get("decision"))
        if d == "allow":
            counts["allow"] += 1
        elif d == "deny":
            counts["deny"] += 1
        else:
            counts["other"] += 1
        ts = _entry_field(e, ("timestamp", "created_at"))
        if ts:
            timestamps.append(str(ts))
    timestamps.sort()
    return {
        "total": len(entries),
        "allow": counts["allow"],
        "deny": counts["deny"],
        "other": counts["other"],
        "earliest": timestamps[0][:10] if timestamps else None,
        "latest": timestamps[-1][:10] if timestamps else None,
    }


def render_summary_line(summary: dict[str, Any]) -> str:
    """One-line rollup, e.g. ``20 entries: 19 allow, 1 deny | 2026-04-25..2026-05-04``."""
    parts = [f"{summary['allow']} allow", f"{summary['deny']} deny"]
    if summary.get("other"):
        parts.append(f"{summary['other']} other")
    counts_str = ", ".join(parts)
    line = f"{summary['total']} entries: {counts_str}"
    if summary.get("earliest") and summary.get("latest"):
        if summary["earliest"] == summary["latest"]:
            line += f" | {summary['earliest']}"
        else:
            line += f" | {summary['earliest']}..{summary['latest']}"
    return line


def render_by_day(entries: list[dict[str, Any]]) -> str:
    """Daily rollup table: ``DATE | total | allow | deny`` sorted newest-first."""
    if not entries:
        return "No audit entries in the requested window."
    by_date: dict[str, dict[str, int]] = {}
    for e in entries:
        ts = _entry_field(e, ("timestamp", "created_at"))
        if not ts:
            continue
        date = str(ts)[:10]
        bucket = by_date.setdefault(date, {"total": 0, "allow": 0, "deny": 0})
        bucket["total"] += 1
        d = _normalize_decision(e.get("decision"))
        if d in ("allow", "deny"):
            bucket[d] += 1
    if not by_date:
        return "No audit entries with timestamps in the requested window."
    cols = ("DATE", "TOTAL", "ALLOW", "DENY")
    rows = [
        (
            date,
            str(by_date[date]["total"]),
            str(by_date[date]["allow"]),
            str(by_date[date]["deny"]),
        )
        for date in sorted(by_date.keys(), reverse=True)
    ]
    widths = [max(len(cols[i]), max(len(r[i]) for r in rows)) for i in range(4)]
    lines = ["  ".join(cols[i].ljust(widths[i]) for i in range(4))]
    lines.append("  ".join("-" * widths[i] for i in range(4)))
    for r in rows:
        lines.append("  ".join(r[i].ljust(widths[i]) for i in range(4)))
    return "\n".join(lines)


def list_agents(client: httpx.Client) -> list[dict[str, Any]]:
    """Return all agents visible to the caller, sorted by name."""
    resp = client.get(
        f"{_api_url()}/api/v1/agents",
        headers={"X-API-Key": _admin_key()},
        params={"limit": 100},
    )
    resp.raise_for_status()
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("agents", []))
    return sorted(items, key=lambda a: str(a.get("name", "")))


def render_agents_table(items: list[dict[str, Any]], *, show_status: bool = False) -> str:
    """Two-column table: NAME, AGENT_ID. Matches the `aid audit` look-and-feel.

    When ``show_status`` is True, non-active agents get a `` (<status>)``
    suffix on the NAME column so revoked/disabled agents are visually
    distinguishable.
    """
    if not items:
        return "No agents visible to this caller."

    def display_name(a: dict[str, Any]) -> str:
        n = str(a.get("name", ""))
        s = a.get("status")
        if show_status and s and s != "active":
            return f"{n} ({s})"
        return n

    name_w = max(len("NAME"), max(len(display_name(a)) for a in items))
    lines = [f"{'NAME'.ljust(name_w)}  AGENT_ID"]
    lines.append(f"{'-' * name_w}  {'-' * 36}")
    for a in items:
        lines.append(f"{display_name(a).ljust(name_w)}  {a.get('id', '')}")
    return "\n".join(lines)


def cmd_agents(args: argparse.Namespace) -> int:
    """Implementation of ``aid agents`` — discover canonical agent names + UUIDs.

    By default lists only active agents (filters out ``status != "active"``).
    Pass ``--all`` to include revoked/disabled agents with a status suffix.
    """
    show_all = bool(getattr(args, "all", False))
    with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
        items = list_agents(client)
    if show_all:
        print(render_agents_table(items, show_status=True))
    else:
        active = [a for a in items if a.get("status", "active") == "active"]
        hidden = len(items) - len(active)
        print(render_agents_table(active))
        if hidden > 0:
            print(f"\n({hidden} non-active agent(s) hidden — pass --all to show)")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Implementation of ``aid audit``."""
    since = parse_duration(args.since)
    with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
        agent_id, agent_name = resolve_agent(client, args.agent)

        if args.verify_chain:
            result = verify_chain(client, agent_id)
            ok = bool(result.get("valid"))
            marker = "OK " if ok else "BAD"
            print(
                f"[{marker}] chain integrity: "
                f"{'VALID' if ok else 'INVALID'} "
                f"(entries={result.get('total_entries')}, "
                f"verified={result.get('entries_verified')})"
            )
            if not ok:
                reason = result.get("reason") or result.get("first_break") or "(no reason)"
                print(f"      first break: {reason}")

        entries = fetch_audit_entries(client, agent_id, since, args.limit)

    decision_filter = getattr(args, "decision", None)
    fetched = len(entries)
    if decision_filter:
        entries = filter_by_decision(entries, decision_filter)

    summary = summarize_entries(entries)
    print(f"Agent: {agent_name} ({agent_id})")
    header = f"Since: {args.since} ago, {render_summary_line(summary)}"
    if decision_filter and fetched != len(entries):
        header += f" (filtered from {fetched} fetched, decision={decision_filter})"
    print(header)
    print()

    if getattr(args, "summary", False):
        # Header already carries the summary; nothing more to print.
        return 0
    if getattr(args, "by_day", False):
        print(render_by_day(entries))
        return 0
    print(render_table(entries, wide=getattr(args, "wide", False)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse tree. Exposed for tests."""
    parser = argparse.ArgumentParser(
        prog="aid",
        description=(
            "AI Identity audit review CLI. Reads AI_IDENTITY_API_URL "
            "(default https://api.ai-identity.co) and AI_IDENTITY_ADMIN_KEY "
            "from the environment. Webhook-driven briefings appear under "
            "the `webhook-receiver` agent by design (Insight #71)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser(
        "audit",
        description="List audit log entries for an agent over a time window.",
    )
    audit.add_argument("--agent", required=True, help="Agent name or UUID.")
    audit.add_argument(
        "--since",
        default="7d",
        help="Lookback window (e.g. 7d, 24h, 30m, 90s). Default: 7d.",
    )
    audit.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max entries to fetch (1-500). Default: 50.",
    )
    audit.add_argument(
        "--verify-chain",
        action="store_true",
        help="Also call the chain-integrity verifier for this agent.",
    )
    audit.add_argument(
        "--decision",
        choices=("allow", "deny"),
        default=None,
        help=(
            "Only show entries with this decision. Matches both the canonical "
            "form (allow|deny) and legacy past-tense form (allowed|denied)."
        ),
    )
    audit.add_argument(
        "--wide",
        action="store_true",
        help="Auto-size columns to widest content (no truncation). Useful when "
        "an endpoint path includes a UUID.",
    )
    audit.add_argument(
        "--summary",
        action="store_true",
        help="Print only the header summary line; suppress the detail table.",
    )
    audit.add_argument(
        "--by-day",
        dest="by_day",
        action="store_true",
        help="Show a daily rollup (DATE TOTAL ALLOW DENY) instead of the per-entry detail table.",
    )
    audit.set_defaults(func=cmd_audit)

    agents = sub.add_parser(
        "agents",
        description=(
            "List agents visible to the caller (canonical name + UUID). "
            "Use this to discover the exact name to pass to `aid audit --agent`. "
            "By default only active agents are shown."
        ),
    )
    agents.add_argument(
        "--all",
        action="store_true",
        help="Include revoked/disabled agents (annotated with their status).",
    )
    agents.set_defaults(func=cmd_agents)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except httpx.HTTPStatusError as exc:
        print(
            f"ERROR: {exc.response.status_code} from {exc.request.url}: {exc.response.text[:200]}",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError as exc:
        print(f"ERROR: network error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
