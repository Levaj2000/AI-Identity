#!/usr/bin/env python3
"""Edge-ingest demo — the "$100 Agent" story, signed and fed to the platform.

Generates the four mandate-draw decision records (three allowed, the fourth
denied over-limit) in exactly the shape the cpex-ocsf-audit plugin emits —
attestation chain, DSSE ECDSA-P256 signature, seam stream stamps — and
streams them into ``POST /api/v1/audit/ingest``, where each record is
cryptographically verified on arrival. Then the tamper beat:

  Act 1  four signed records            → 4x verified, chain positions 1-4
  Act 2  replay the same batch          → 4x duplicate, nothing re-stored
  Act 3  a tampered copy (edited after  → quarantined: fingerprint mismatch,
         signing)                          stored verbatim with the reason
  Act 4  a record after a lost epoch    → verified WITH anomaly: the gap is
         (stream_seq jumps)                surfaced, the chain re-anchors

Offline mode writes the signed NDJSON + demo public key to disk instead —
the same file feeds the immutable-ledger cpex adapter, so one artifact
drives both sinks of the joint demo:
    python3 scripts/demo_edge_ingest.py --out /tmp/spend-story

Online mode (API running; deps: the api venv — cryptography, rfc8785):
    export AI_IDENTITY_TOKEN=<clerk session token>   # to auto-register the edge
    python3 scripts/demo_edge_ingest.py
    # or with a pre-registered edge:
    EDGE_INGEST_KEY=aid_edge_... python3 scripts/demo_edge_ingest.py

Optional: API_URL (default http://localhost:8000), DEMO_CHAIN_UID.
The signing key is a fixed demo scalar — never a real credential; the
platform only ever sees the public half.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

import rfc8785
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

API_URL = os.environ.get("API_URL", "http://localhost:8000")
CHAIN_UID = os.environ.get("DEMO_CHAIN_UID", "edge-demo-100-dollar-agent")
STREAM_ID = "gw-demo/boot-1"
TIMEOUT = 20

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Fixed demo scalar (public half registered with the platform; the demo is
# about verification, not key custody — a real edge uses its own keypair).
DEMO_KEY = ec.derive_private_key(0x0100D011A2A6E27, ec.SECP256R1())

# (seq, request id, time, amount, allowed, remaining after)
DRAWS = [
    (1, "corr-d1a04f10", "2026-08-22T17:00:01.000Z", "40.00", True, "60.00"),
    (2, "corr-d2b93c22", "2026-08-22T17:00:02.000Z", "35.00", True, "25.00"),
    (3, "corr-d3c71e08", "2026-08-22T17:00:03.000Z", "20.00", True, "5.00"),
    (4, "corr-d4e55b37", "2026-08-22T17:00:04.000Z", "15.00", False, "5.00"),
]


def demo_public_key_pem(key=DEMO_KEY) -> str:
    return (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


def _covered_bytes(event: dict) -> bytes:
    # The emitter's sign::signing_input rule, verbatim.
    ev = copy.deepcopy(event)
    att = ev["attestation_list"][0]
    att.pop("fingerprint", None)
    att.pop("signatures", None)
    ev["unmapped"].pop("signature_b64", None)
    ev["unmapped"].pop("signature_key_id", None)
    return rfc8785.dumps(ev)


def _dsse_pae(payload: bytes) -> bytes:
    t = b"application/vnd.ocsf.event+json"
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def _sign_and_chain(event: dict, prev: tuple[str, str] | None, key) -> tuple[dict, tuple[str, str]]:
    if prev is not None:
        event["attestation_list"][0]["prev_event"] = {
            "uid": prev[0],
            "type_uid": 600399,
            "fingerprint": {"algorithm_id": 3, "value": prev[1]},
        }
    cb = _covered_bytes(event)
    fingerprint = hashlib.sha256(cb).hexdigest()
    event["attestation_list"][0]["fingerprint"] = {
        "algorithm_id": 3,
        "encoding_id": 1,
        "serialization_id": 2,
        "value": fingerprint,
    }
    signature = key.sign(_dsse_pae(cb), ec.ECDSA(hashes.SHA256()))
    # Signature descriptor rides attestation.signatures (outside the hashed
    # bytes, like fingerprint) — the emitter's shape per AID-EMIT-1 §5.
    event["attestation_list"][0]["signatures"] = [
        {"algorithm_id": 3, "algorithm": "ECDSA", "serialization_id": 5, "serialization": "DSSE"}
    ]
    event["unmapped"]["signature_b64"] = base64.b64encode(signature).decode()
    event["unmapped"]["signature_key_id"] = "edge-demo-key-1"
    return event, (event["metadata"]["uid"], fingerprint)


def _draw_record(seq: int, req: str, ts: str, amount: str, allowed: bool, remaining: str) -> dict:
    # Field shapes match the committed cpex-ocsf-audit sample records
    # (SAMPLE-OUTPUT-DECISIONS.md records 5 and 3): a delegated mandate
    # draw, denied over-limit on the fourth. metadata.uid is what a real
    # decision record will carry once spec §4 emitter item 5 lands.
    event = {
        "action": "Allowed",
        "action_id": 1,
        "activity_id": 99,
        "activity_name": "Invoke Tool",
        "actor": {"roles": ["hr"], "user": {"groups": [], "uid": "alice@corp.com"}},
        "api": {"request": {"uid": f"call-{seq}"}},
        "category_uid": 6,
        "class_uid": 6003,
        "delegation": {
            "actor_subject_uid": "agent-7",
            "chain": [
                {
                    "audience": "payments-mcp",
                    "scopes_granted": ["spend"],
                    "subject_uid": "agent-7",
                    "timestamp": "1970-01-01T00:00:00+00:00",
                    "ttl_seconds": 300,
                }
            ],
            "depth": 1,
            "origin_subject_uid": "alice@corp.com",
        },
        "disposition": "Allowed",
        "disposition_id": 1,
        "metadata": {
            "uid": f"draw-{seq:03d}",
            "product": {"name": "AI Identity OCSF Audit", "vendor_name": "AI Identity"},
            "profiles": ["ai_operation", "security_control", "record_integrity"],
            "version": "1.9.0",
        },
        "severity_id": 1,
        "time": ts,
        "tool": {"name": "make_purchase", "namespace": "procurement", "uid": f"call-{seq}"},
        "type_uid": 600399,
        "attestation_list": [
            {"uid": f"att-draw-{seq:03d}", "chain_uid": CHAIN_UID, "authority_uid": "org-demo"}
        ],
        "unmapped": {
            "cmf.request.request_id": req,
            "cmf.security.labels": ["FINANCIAL"],
            "cpex.stream": {
                "epoch": 1,
                "stream_id": STREAM_ID,
                "stream_seq": seq,
                "emission_seq": seq,
            },
        },
    }
    if allowed:
        event["unmapped"]["cpex.decision"] = {
            "steps": [
                {"action": "allowed", "phase": "sequential", "plugin": "mandate-check"},
                {"action": "allowed", "phase": "sequential", "plugin": "cedar-pdp"},
            ],
            "verdict": "allow",
        }
    else:
        reason = (
            f"mandate-check: draw {amount} exceeds remaining {remaining} "
            f"of 100.00 mandate for agent-7"
        )
        event.update(
            {
                "action": "Denied",
                "action_id": 2,
                "disposition": "Blocked",
                "disposition_id": 2,
                "status_code": "mandate_exceeded",
                "status_detail": reason,
                "status_id": 2,
            }
        )
        event["unmapped"]["cpex.decision"] = {
            "steps": [{"action": "denied", "phase": "sequential", "plugin": "mandate-check"}],
            "verdict": {"deny": {"code": "mandate_exceeded", "reason": reason}},
        }
    return event


def build_story(key=DEMO_KEY) -> list[dict]:
    """The four signed, chained draw records of the $100-agent story."""
    events, prev = [], None
    for seq, req, ts, amount, allowed, remaining in DRAWS:
        event = _draw_record(seq, req, ts, amount, allowed, remaining)
        event, prev = _sign_and_chain(event, prev, key)
        events.append(event)
    return events


def build_tampered(story: list[dict]) -> dict:
    """A copy of draw 2 edited AFTER signing — the forgery the math catches."""
    tampered = copy.deepcopy(story[1])
    tampered["metadata"]["uid"] = "draw-evil"
    tampered["status_detail"] = "amount quietly rewritten"
    return tampered


def build_gap_record(story: list[dict], key=DEMO_KEY) -> dict:
    """A crypto-valid record whose predecessors were lost — seq jumps 4 → 7."""
    event = _draw_record(7, "corr-d7f90a11", "2026-08-22T17:00:07.000Z", "1.00", True, "4.00")
    last = story[-1]
    prev = (last["metadata"]["uid"], last["attestation_list"][0]["fingerprint"]["value"])
    event, _ = _sign_and_chain(event, prev, key)
    return event


def ndjson(events: list[dict]) -> bytes:
    return b"\n".join(json.dumps(e, sort_keys=True).encode() for e in events)


# ── Online demo ─────────────────────────────────────────────────────


def _die(msg: str) -> None:
    print(f"{RED}FATAL{RESET} {msg}", file=sys.stderr)
    sys.exit(2)


def _post(path: str, body: bytes, headers: dict) -> dict:
    req = urllib.request.Request(API_URL + path, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        _die(f"POST {path} → {exc.code}: {exc.read().decode()[:300]}")


def _register_edge() -> str:
    token = os.environ.get("AI_IDENTITY_TOKEN")
    if not token:
        _die(
            "set EDGE_INGEST_KEY (pre-registered edge) or AI_IDENTITY_TOKEN "
            "(Clerk session token, to register one)"
        )
    data = _post(
        "/api/v1/edges",
        json.dumps(
            {
                "name": "Edge demo — $100 Agent",
                "chain_uid": CHAIN_UID,
                "verify_key_pem": demo_public_key_pem(),
                "key_id": "edge-demo-key-1",
            }
        ).encode(),
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    print(f"registered edge {BOLD}{data['id']}{RESET} (chain {CHAIN_UID})")
    return data["ingest_key"]


def _ingest(ingest_key: str, events: list[dict]) -> dict:
    return _post(
        "/api/v1/audit/ingest",
        ndjson(events),
        {"Authorization": f"Bearer {ingest_key}", "Content-Type": "application/x-ndjson"},
    )


def _show(title: str, response: dict) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    for r in response["results"]:
        status = r["status"]
        color = {"verified": GREEN, "quarantined": RED}.get(status, YELLOW)
        line = f"  {color}{status:<11}{RESET} {r.get('uid') or r.get('dedupe_key') or '—'}"
        if r.get("chain_position"):
            line += f"  chain #{r['chain_position']}"
        if r.get("reason"):
            line += f"  {RED}{r['reason']}{RESET}"
        if r.get("anomalies"):
            line += f"  {YELLOW}{r['anomalies']}{RESET}"
        print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        metavar="PREFIX",
        help="offline: write PREFIX.jsonl (signed story) + PREFIX.pub.pem and exit",
    )
    args = parser.parse_args()

    story = build_story()

    if args.out:
        with open(f"{args.out}.jsonl", "wb") as f:
            f.write(ndjson(story) + b"\n")
        with open(f"{args.out}.pub.pem", "w") as f:
            f.write(demo_public_key_pem())
        print(f"wrote {args.out}.jsonl (4 signed records) and {args.out}.pub.pem")
        return

    ingest_key = os.environ.get("EDGE_INGEST_KEY") or _register_edge()

    _show(
        "Act 1 — the $100 agent: three draws land, the fourth is denied", _ingest(ingest_key, story)
    )
    _show(
        "Act 2 — replaying the batch: at-least-once, nothing re-stored", _ingest(ingest_key, story)
    )
    _show(
        "Act 3 — a record edited after signing: the math catches it",
        _ingest(ingest_key, [build_tampered(story)]),
    )
    _show(
        "Act 4 — after a lost epoch: the gap is surfaced, the chain re-anchors",
        _ingest(ingest_key, [build_gap_record(story)]),
    )
    print(
        f"\n{GREEN}done{RESET} — every outcome above is stored org-scoped; "
        "quarantined and anomalous rows carry their reasons verbatim."
    )


if __name__ == "__main__":
    main()
