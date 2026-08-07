#!/usr/bin/env python3
"""Biscuit trust-boundary demo — a mandate crossing trust domains as a token.

The companion walk to demo_mandate_overspend.py, one layer down the stack:
the $100 grant leaves home as a signed Biscuit token, gets narrowed offline
for a sub-agent, and every draw goes through the GATEWAY's enforce path
(policy + Biscuit checks + authoritative settlement), not the mandate API.

  1. Issue a signed $100 mandate, then mint its Biscuit — and print the
     authority block: the grant is readable Datalog inside the token
  2. Parent agent draws $30.00 through the gateway         → ALLOW
  3. Parent attenuates the token to a $20.00 ceiling and hands it to a
     sub-agent — offline, no call to any service            (the boundary)
  4. Sub-agent draws $15.00 with the narrowed token         → ALLOW
  5. Sub-agent tries $40.00 → DENIED BY THE TOKEN ITSELF, before the
     mandate service is even consulted (check n°… in block n°1)
  6. Parent settles an out-of-band $405.00 → recorded, mandate EXCEEDED
  7. One flipped byte in the token → signature verification fails
  8. Closer: the whole walk sits in the chained OCSF export, biscuit
     revocation ids included

Prerequisites (all local):
    kubectl -n ai-identity port-forward svc/mandate-service 8003:8003 &
    # gateway running locally with BISCUIT_ROOT_KEY_PEM + MANDATE_DRAW_TOKEN set,
    # and DEMO_AGENT_ID must have an active policy allowing DEMO_ENDPOINT
    export AI_IDENTITY_TOKEN=<clerk session token>
    export DEMO_AGENT_ID=<platform agent UUID in the demo org>
    pip install biscuit-python==0.4.0   # for the offline attenuation step
    python3 scripts/demo_biscuit_trust_boundary.py

Optional env: MANDATE_URL (default http://localhost:8003),
GATEWAY_URL (default http://localhost:8002), DEMO_ORG_ID,
DEMO_ENDPOINT (default /v1/commerce/checkout).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MANDATE_URL = os.environ.get("MANDATE_URL", "http://localhost:8003")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8002")
ENDPOINT = os.environ.get("DEMO_ENDPOINT", "/v1/commerce/checkout")
TIMEOUT = 20

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _die(msg: str) -> None:
    print(f"{RED}FATAL{RESET} {msg}", file=sys.stderr)
    sys.exit(2)


def _request(url: str, method: str, body: dict | None, headers: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            _die(f"{method} {url} → HTTP {e.code} (unparseable body)")
    except urllib.error.URLError as e:
        _die(f"{method} {url} → {e.reason} (is the service running / port-forwarded?)")
    raise AssertionError("unreachable")


def _mandate_api(method: str, path: str, body: dict | None = None) -> dict:
    token = os.environ.get("AI_IDENTITY_TOKEN") or _die("AI_IDENTITY_TOKEN not set")
    status, parsed = _request(
        MANDATE_URL + path,
        method,
        body,
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    if status >= 400:
        _die(f"{method} {path} → HTTP {status}: {json.dumps(parsed)[:300]}")
    return parsed


def _cents(c: int | None) -> str:
    return f"${c / 100:,.2f}" if c is not None else "—"


def _gateway_draw(
    agent_id: str,
    token: str,
    amount_cents: int,
    *,
    label: str,
    settlement: bool = False,
    reference: str = "",
) -> tuple[int, dict]:
    params = {
        "agent_id": agent_id,
        "endpoint": ENDPOINT,
        "method": "POST",
        "spend_amount_cents": str(amount_cents),
        "spend_scope": "spend:commerce",
        "spend_settlement": "true" if settlement else "false",
    }
    if reference:
        params["spend_reference"] = reference
    status, body = _request(
        f"{GATEWAY_URL}/gateway/enforce?{urllib.parse.urlencode(params)}",
        "POST",
        None,
        {"X-Agent-Mandate": token},
    )
    draw = body.get("mandate") or {}
    if body.get("decision") == "allow":
        # A settlement can be accepted AND breach the grant — that's the point.
        verdict = f"{RED}EXCEEDED{RESET}" if draw.get("exceeded") else f"{GREEN}ALLOW{RESET}"
        tail = f"spent {_cents(draw.get('spent_cents'))} of {_cents(draw.get('limit_cents'))}"
        if draw.get("exceeded"):
            tail += f"  [recorded — mandate now {draw.get('status')}]"
    else:
        exceeded = bool(draw.get("exceeded"))
        verdict = f"{RED}EXCEEDED{RESET}" if exceeded else f"{RED}DENIED{RESET}"
        tail = f"[{body.get('deny_reason', '?')}] {body.get('message', '')[:80]}"
    mode = " (settlement)" if settlement else ""
    print(f"  {label:<34} {_cents(amount_cents):>10}{mode:13} → {verdict:<18} {tail}")
    return status, body


def _show_receipt(body: dict, root_public_key: str) -> None:
    """The return path: verify the leaf's signed receipt as the delegator would."""
    from common.biscuit import verify_receipt

    bundle = body.get("receipt")
    if not bundle:
        print(f"    {YELLOW}(no receipt returned){RESET}")
        return
    ok = verify_receipt(bundle, root_public_key)
    r = bundle["receipt"]
    mark = f"{GREEN}✓ verified{RESET}" if ok else f"{RED}✗ INVALID{RESET}"
    rev = (r.get("revocation_id") or "")[:12]
    print(
        f"    ⤶ receipt {mark} offline (same root key as the token) — "
        f"{r['decision']}"
        + (f" [{r.get('deny_reason')}]" if r.get("deny_reason") else "")
        + (f", token {rev}…" if rev else "")
    )


def main() -> int:
    try:
        from biscuit_auth import Biscuit

        from common.biscuit import attenuate_spend_ceiling
        from common.biscuit.tokens import _public_key  # noqa: PLC2701 — demo-only peek
    except ImportError:
        _die("biscuit-python not installed — pip install biscuit-python==0.4.0")

    agent_id = os.environ.get("DEMO_AGENT_ID") or _die("DEMO_AGENT_ID not set")
    org_id = os.environ.get("DEMO_ORG_ID", "")

    print(f"{BOLD}Biscuit trust-boundary walk — gateway @ {GATEWAY_URL}{RESET}\n")

    # 1 — grant, then mint the presentation credential
    mandate = _mandate_api(
        "POST",
        "/api/v1/mandates",
        {
            "subject_agent_id": agent_id,
            "subject_org_id": org_id or "demo-org",
            "scope": ["spend:commerce"],
            "spend_limit": {"limit_cents": 10_000, "currency": "USD"},
            "metadata": {"purpose": "Biscuit trust-boundary demo"},
        },
    )
    mid = mandate["mandate_id"]
    print(
        f"{GREEN}issued{RESET} {BOLD}{mid}{RESET} — $100.00 limit, "
        f"signed {mandate['signatures'][0]['algorithm']}"
    )

    # BISCUIT_MINT=local mints client-side from BISCUIT_ROOT_KEY_PEM_FILE —
    # for driving the demo against a deployed mandate service that predates
    # the /biscuit endpoint. The mandate itself (issue, signature, spend,
    # audit) still comes from the real service either way.
    if os.environ.get("BISCUIT_MINT") == "local":
        import datetime as _dt

        from common.biscuit import mint_mandate_biscuit

        pem = Path(os.environ["BISCUIT_ROOT_KEY_PEM_FILE"]).read_text()
        _iso = lambda s: _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
        m = mint_mandate_biscuit(
            private_key_pem=pem,
            mandate_id=mid,
            subject_agent_id=agent_id,
            subject_org_id=mandate["subject"]["org_id"],
            scope=mandate["scope"],
            valid_from=_iso(mandate["valid_from"]),
            valid_until=_iso(mandate["valid_until"]) if mandate.get("valid_until") else None,
            limit_cents=mandate["spend_limit"]["limit_cents"]
            if mandate.get("spend_limit")
            else None,
            currency=mandate["spend_limit"]["currency"] if mandate.get("spend_limit") else "USD",
        )
        minted = {"token": m.token, "root_public_key": m.root_public_key}
    else:
        minted = _mandate_api("POST", f"/api/v1/mandates/{mid}/biscuit")
    parent_token = minted["token"]
    print(f"{GREEN}minted{RESET} Biscuit ({len(parent_token)} chars) — the grant, as Datalog:\n")
    authority = Biscuit.from_base64(parent_token, _public_key(minted["root_public_key"]))
    for line in authority.block_source(0).strip().splitlines():
        print(f"    {CYAN}{line}{RESET}")
    print()

    # 2 — parent draws through the gateway
    _gateway_draw(agent_id, parent_token, 3_000, label="parent draw", reference="ord_2001")

    # 3 — the trust boundary: narrow the token OFFLINE and hand it over
    sub_token = attenuate_spend_ceiling(
        parent_token, minted["root_public_key"], ceiling_cents=2_000
    )
    print(
        f"\n  {YELLOW}⤷ parent attenuates to a $20.00 ceiling and hands the token "
        f"to a sub-agent — no service was called{RESET}"
    )

    # 4 / 5 — the narrowed token enforces itself; every outcome yields a
    # signed receipt back to the presenter (the return path of the loop)
    _, body = _gateway_draw(
        agent_id, sub_token, 1_500, label="sub-agent draw", reference="ord_2002"
    )
    _show_receipt(body, minted["root_public_key"])
    _, body = _gateway_draw(
        agent_id, sub_token, 4_000, label="sub-agent over-ceiling", reference="ord_2003"
    )
    print(
        f"    {YELLOW}↑ denied by the token's own attenuation check, offline — "
        f"the mandate service was never consulted{RESET}"
    )
    _show_receipt(body, minted["root_public_key"])
    print(
        f"    {YELLOW}⤶ the delegator now holds signed proof of BOTH: what its "
        f"delegate did, and what it was refused{RESET}"
    )

    # 6 — out-of-band settlement breaches the grant
    print()
    _gateway_draw(
        agent_id,
        parent_token,
        40_500,
        label="parent settlement",
        settlement=True,
        reference="ord_2004",
    )

    # 7 — tamper finale
    print()
    flipped = bytearray(parent_token.encode())
    flipped[len(flipped) // 2] ^= 0x01
    _gateway_draw(
        agent_id,
        flipped.decode(errors="ignore"),
        100,
        label="tampered token",
        reference="ord_2005",
    )

    print(f"""
{BOLD}The evidence trail:{RESET} every step above — allows, the offline token
denial, the breach, the tamper rejection — is in the chained audit log with
credential_format=biscuit and per-token revocation ids:
  GET /api/v1/audit/report?format=ocsf&agent_id={agent_id}
Everyone can verify a Biscuit; the OCSF export is the court-ready record
of what it was used for.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
