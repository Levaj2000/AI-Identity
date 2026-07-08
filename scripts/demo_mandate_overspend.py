#!/usr/bin/env python3
"""Agent-commerce overspend demo — drives the $100-mandate → $500-spend walk.

Stages the full story against a running Mandate Service, exercising BOTH
spend modes, then points at the OCSF export where the chained evidence lives:

  1. Issue a signed mandate: $100.00 spend limit (spend:commerce scope)
  2. Three accepted spends totaling $95.00        → allow, allow, allow
  3. ENFORCE:   attempt $40.50 (would cross)      → DENIED, budget intact
  4. SETTLE:    $405.00 already-moved settlement  → recorded, mandate EXCEEDED
  5. Post-breach spend attempt                    → DENIED (mandate_inactive)
  6. /verify on the final document                → within_spend_limit: false

Every step lands in the hash-chained audit log, so afterwards the walk is
visible in `GET /api/v1/audit/report?format=ocsf&agent_id=...` as Allowed/
Denied API-Activity events carrying an `unmapped.mandate` block — and the
export bundle verifies offline with the standalone CLI.

Usage (the mandate service is cluster-internal; port-forward first):
    kubectl -n ai-identity port-forward svc/mandate-service 8003:8003 &
    export AI_IDENTITY_TOKEN=<clerk session token>   # devtools: copy(await Clerk.session.getToken())
    export DEMO_AGENT_ID=<platform agent UUID in the demo org>
    python3 scripts/demo_mandate_overspend.py

Optional: MANDATE_URL (default http://localhost:8003), DEMO_ORG_ID.
Idempotent-ish: issues a fresh mandate every run; old ones stay as history.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("MANDATE_URL", "http://localhost:8003")
TIMEOUT = 20

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _die(msg: str) -> None:
    print(f"{RED}FATAL{RESET} {msg}", file=sys.stderr)
    sys.exit(2)


def _req(method: str, path: str, body: dict | None = None) -> dict:
    token = os.environ.get("AI_IDENTITY_TOKEN")
    if not token:
        _die("AI_IDENTITY_TOKEN not set (Clerk session token)")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        URL + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        _die(f"{method} {path} → HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        _die(f"{method} {path} → {e.reason} (is the port-forward running?)")
    raise AssertionError("unreachable")


def _cents(c: int | None) -> str:
    return f"${c / 100:,.2f}" if c is not None else "—"


def _spend(
    mandate_id: str,
    amount_cents: int,
    *,
    reference: str,
    description: str,
    settlement: bool = False,
) -> dict:
    r = _req(
        "POST",
        f"/api/v1/mandates/{mandate_id}/spend",
        {
            "amount_cents": amount_cents,
            "currency": "USD",
            "reference": reference,
            "description": description,
            "settlement": settlement,
        },
    )
    verdict = (
        f"{RED}EXCEEDED{RESET}"
        if r["exceeded"]
        else (f"{GREEN}allowed{RESET}" if r["accepted"] else f"{RED}DENIED{RESET}")
    )
    mode = " (settlement)" if settlement else ""
    print(
        f"  spend {_cents(amount_cents):>10}{mode:13} → {verdict:<18} "
        f"spent {_cents(r['spent_cents'])} of {_cents(r['limit_cents'])}"
        + (f"  [{r['deny_reason']}]" if r.get("deny_reason") else "")
    )
    return r


def main() -> int:
    agent_id = os.environ.get("DEMO_AGENT_ID") or _die("DEMO_AGENT_ID not set")
    org_id = os.environ.get("DEMO_ORG_ID", "")

    print(f"{BOLD}Agent-commerce overspend walk — mandate service @ {URL}{RESET}\n")

    # 1 — grant the monetary authority
    issue_body: dict = {
        "subject_agent_id": agent_id,
        "subject_org_id": org_id or "demo-org",
        "scope": ["spend:commerce"],
        "spend_limit": {"limit_cents": 10_000, "currency": "USD"},
        "metadata": {"purpose": "IBM demo — agent commerce overspend walk"},
    }
    mandate = _req("POST", "/api/v1/mandates", issue_body)
    mid = mandate["mandate_id"]
    n_sigs = len(mandate["signatures"])
    print(
        f"{GREEN}issued{RESET} {BOLD}{mid}{RESET} — $100.00 limit, "
        f"{n_sigs} signature(s) ({mandate['signatures'][0]['algorithm']})\n"
    )

    # 2 — normal commerce, inside the limit
    _spend(mid, 2_500, reference="ord_1001", description="running socks")
    _spend(mid, 3_000, reference="ord_1002", description="water bottle")
    _spend(mid, 4_000, reference="ord_1003", description="gym bag")

    # 3 — prevention: the gateway-style enforce path says no
    print()
    _spend(mid, 4_050, reference="ord_1004", description="trainers (over budget)")

    # 4 — detection: money moved out-of-band, settlement records the breach
    _spend(
        mid, 40_500, reference="ord_1005", description="limited-edition sneakers", settlement=True
    )

    # 5 — the mandate is now locked
    _spend(mid, 100, reference="ord_1006", description="post-breach attempt")

    # 6 — independent verification flags it
    final = _req("GET", f"/api/v1/mandates/{mid}")
    verdict = _req("POST", "/api/v1/mandates/verify", {"mandate": final})
    print(f"\n{BOLD}/verify{RESET} on the final document:")
    for check, passed in verdict["checks"].items():
        mark = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {mark} {check}")
    if verdict.get("error"):
        print(f"  {YELLOW}{verdict['error']}{RESET}")

    print(f"""
{BOLD}Next on stage:{RESET} the whole walk is now in the chained audit trail —
  GET /api/v1/audit/report?format=ocsf&agent_id={agent_id}
Each event carries an unmapped.mandate block (amounts, cumulative spend,
limit, deny_reason); the two denials read as OCSF `Denied` / severity 3.
Export the bundle and run the offline verifier for the tamper finale.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
