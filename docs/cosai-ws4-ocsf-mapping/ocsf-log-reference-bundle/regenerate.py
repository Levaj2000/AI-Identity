#!/usr/bin/env python3
"""Regenerate the OCSF reference bundle from a fresh production export.

Input: the NDJSON file downloaded from
``GET /api/v1/audit/report?format=ocsf`` (org-wide scope, demo org
``f3576cf6``) — via the dashboard Case File page or curl with a Clerk
bearer token.

What it does:
1. Validates every event is on the FINAL #1661 attestation shape
   (record_integrity profile, fingerprint hashes, ``signatures`` array,
   ``attestation.uid``) and rejects the old draft shape (string
   ``entry_hash``, singular ``signature``, ``sequence`` field).
2. Verifies the org hash chain end-to-end (``prev_entry_hash`` linkage in
   ``org_chain_seq`` order).
3. Verifies each per-event ECDSA-P256-SHA256 signature against the public
   JWKS (https://api.ai-identity.co/.well-known/ai-identity-public-keys.json)
   — DER signature over ``bytes.fromhex(entry_hash.value)``. Requires the
   ``cryptography`` package; skipped with a warning if unavailable.
4. Writes ``production-ocsf-full-export.ocsf.ndjson`` (verbatim copy) and
   ``production-ocsf-excerpt.ocsf.ndjson`` (default: org_chain_seq 16-22,
   the QA-eae97318 lifecycle story the README walks through).
5. Fills the README between the ``REGEN:ANATOMY`` / ``REGEN:STATS`` markers
   from the actual export, so the walkthrough can never drift from the files.

Usage:
    python3 regenerate.py <fresh-export.ndjson> [--excerpt-seq 16-22]
        [--jwks <url-or-path>] [--bundle-dir <dir>] [--skip-signatures]

No local file yet? Fetch + regenerate in one step (needs a Clerk session
token — dashboard tab → devtools console → `await Clerk.session.getToken()`;
tokens live ~60s, so run this right after copying):

    AI_IDENTITY_TOKEN=<jwt> python3 regenerate.py --fetch

The dashboard's own OCSF button is single-agent scope; the bundle uses the
org-wide export, which is why --fetch hits the endpoint directly.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_JWKS_URL = "https://api.ai-identity.co/.well-known/ai-identity-public-keys.json"
DEMO_ORG_ID = "f3576cf6-87ff-4c07-b446-e6ac526236a5"
EXPORT_URL = f"https://api.ai-identity.co/api/v1/audit/report?format=ocsf&org_id={DEMO_ORG_ID}"
ANATOMY_BEGIN, ANATOMY_END = "<!-- REGEN:ANATOMY -->", "<!-- /REGEN:ANATOMY -->"
STATS_BEGIN, STATS_END = "<!-- REGEN:STATS -->", "<!-- /REGEN:STATS -->"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ── 1. Shape validation ─────────────────────────────────────────────


def validate_event_shape(ev: dict, line_no: int) -> list[str]:
    """Return a list of shape problems for one event (empty = conformant)."""
    problems: list[str] = []
    ctx = f"line {line_no}"

    if ev.get("class_uid") != 6003:
        problems.append(f"{ctx}: class_uid != 6003")
    profiles = ev.get("metadata", {}).get("profiles", [])
    if "ai_operation" not in profiles:
        problems.append(f"{ctx}: ai_operation profile missing")

    att = ev.get("attestation")
    if att is None:
        # Legal (row without chain data) but unexpected for this org.
        problems.append(f"{ctx}: no attestation object")
        return problems

    if "record_integrity" not in profiles:
        problems.append(f"{ctx}: attestation present but record_integrity profile not declared")

    # Old-draft-shape tripwires (what this regeneration exists to replace).
    if isinstance(att.get("entry_hash"), str):
        problems.append(f"{ctx}: OLD SHAPE — entry_hash is a string, not a fingerprint object")
    if "signature" in att:
        problems.append(f"{ctx}: OLD SHAPE — singular 'signature' field")
    if "sequence" in att:
        problems.append(f"{ctx}: OLD SHAPE — 'sequence' field (removed in final #1661)")

    if not att.get("uid"):
        problems.append(f"{ctx}: attestation.uid missing")

    org_chain_seq = ev.get("unmapped", {}).get("org_chain_seq")
    for fp_name in ("entry_hash", "prev_entry_hash"):
        fp = att.get(fp_name)
        if fp is None:
            continue  # prev_entry_hash may be absent on the genesis event
        if not isinstance(fp, dict):
            problems.append(f"{ctx}: {fp_name} is not a fingerprint object")
            continue
        if fp.get("algorithm_id") != 99 or fp.get("algorithm") != "HMAC-SHA-256":
            problems.append(
                f"{ctx}: {fp_name} must be algorithm_id 99 / HMAC-SHA-256, "
                f"got {fp.get('algorithm_id')}/{fp.get('algorithm')}"
            )
        value = fp.get("value", "")
        # The chain's first row stores the literal sentinel "GENESIS" as its
        # prev hash, and the emitter passes it through — accept it there only
        # (a mid-chain sentinel would also break linkage verification).
        if fp_name == "prev_entry_hash" and value == "GENESIS" and org_chain_seq == 1:
            continue
        if not _HEX64.match(value):
            problems.append(f"{ctx}: {fp_name}.value is not 64-char lowercase hex")

    sigs = att.get("signatures")
    if not isinstance(sigs, list) or not sigs:
        problems.append(f"{ctx}: attestation.signatures missing/empty (required in final shape)")
    else:
        sig = sigs[0]
        if sig.get("algorithm_id") != 3 or sig.get("algorithm") != "ECDSA-P256-SHA256":
            problems.append(f"{ctx}: signatures[0] is not algorithm_id 3 / ECDSA-P256-SHA256")
        digest = sig.get("digest", {})
        if digest.get("value") != att.get("entry_hash", {}).get("value"):
            problems.append(f"{ctx}: signatures[0].digest does not match entry_hash")

    unmapped = ev.get("unmapped", {})
    if not unmapped.get("signature_b64"):
        problems.append(f"{ctx}: unmapped.signature_b64 missing")
    if not unmapped.get("signature_key_id"):
        problems.append(f"{ctx}: unmapped.signature_key_id missing")

    return problems


# ── 2. Chain verification ───────────────────────────────────────────


def verify_chain(events: list[dict]) -> tuple[int, int]:
    """Verify prev_entry_hash linkage in org_chain_seq order.

    Returns (links_checked, first_seq). Fails hard on a broken link.
    """
    seqd = [
        (e["unmapped"]["org_chain_seq"], e)
        for e in events
        if "org_chain_seq" in e.get("unmapped", {})
    ]
    if len(seqd) != len(events):
        fail(f"{len(events) - len(seqd)} events have no unmapped.org_chain_seq")
    seqd.sort(key=lambda t: t[0])
    seqs = [s for s, _ in seqd]
    if seqs != list(range(seqs[0], seqs[0] + len(seqs))):
        fail(f"org_chain_seq is not contiguous: {seqs[0]}..{seqs[-1]} with {len(seqs)} events")

    links = 0
    for (_, prev_ev), (seq, ev) in zip(seqd, seqd[1:], strict=False):
        prev_hash = prev_ev["attestation"]["entry_hash"]["value"]
        claimed = ev["attestation"].get("prev_entry_hash", {}).get("value")
        if claimed != prev_hash:
            fail(
                f"chain BROKEN at org_chain_seq {seq}: prev_entry_hash != seq {seq - 1} entry_hash"
            )
        links += 1
    return links, seqs[0]


# ── 3. Signature verification (public JWKS, no secrets) ────────────


def load_jwks(source: str) -> dict[str, object]:
    """Return {kid: EllipticCurvePublicKey} from a JWKS URL or file path."""
    from cryptography.hazmat.primitives.asymmetric import ec

    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:  # noqa: S310
            doc = json.load(resp)
    else:
        doc = json.loads(Path(source).read_text())

    def b64u_to_int(v: str) -> int:
        return int.from_bytes(base64.urlsafe_b64decode(v + "=" * (-len(v) % 4)), "big")

    keys = {}
    for jwk in doc.get("keys", []):
        if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
            continue
        pub = ec.EllipticCurvePublicNumbers(
            b64u_to_int(jwk["x"]), b64u_to_int(jwk["y"]), ec.SECP256R1()
        ).public_key()
        keys[jwk["kid"]] = pub
    if not keys:
        fail(f"no usable P-256 keys in JWKS from {source}")
    return keys


def verify_signatures(events: list[dict], jwks: dict) -> int:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    verified = 0
    for ev in events:
        seq = ev.get("unmapped", {}).get("org_chain_seq")
        key_id = ev["unmapped"]["signature_key_id"]
        pub = jwks.get(key_id)
        if pub is None:
            fail(f"seq {seq}: signature_key_id not present in JWKS: {key_id}")
        sig = base64.b64decode(ev["unmapped"]["signature_b64"])
        message = bytes.fromhex(ev["attestation"]["entry_hash"]["value"])
        try:
            pub.verify(sig, message, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            fail(f"seq {seq}: ECDSA signature INVALID")
        verified += 1
    return verified


# ── 4/5. Bundle + README emission ───────────────────────────────────


def truncate_for_display(ev: dict) -> dict:
    """Shorten hashes / signature bytes for the README anatomy block."""
    disp = copy.deepcopy(ev)

    def trunc(s: str, keep: int = 16) -> str:
        return s[:keep] + "…" if isinstance(s, str) and len(s) > keep + 1 else s

    att = disp.get("attestation", {})
    for fp_name in ("entry_hash", "prev_entry_hash"):
        if fp_name in att:
            att[fp_name]["value"] = trunc(att[fp_name]["value"])
    for sig in att.get("signatures", []):
        if "digest" in sig:
            sig["digest"]["value"] = trunc(sig["digest"]["value"])
    if "unmapped" in disp:
        if "signature_b64" in disp["unmapped"]:
            disp["unmapped"]["signature_b64"] = trunc(disp["unmapped"]["signature_b64"], 24)
        if "signature_key_id" in disp["unmapped"]:
            # Keep the tail — the key ring / version is the readable part.
            kid = disp["unmapped"]["signature_key_id"]
            if len(kid) > 60:
                disp["unmapped"]["signature_key_id"] = "projects/…/" + "/".join(kid.split("/")[-4:])
    if "actor" in disp:
        disp["actor"]["user"]["uid"] = trunc(disp["actor"]["user"]["uid"], 8)
    return disp


def inject(readme: str, begin: str, end: str, content: str, inline: bool = False) -> str:
    if begin not in readme or end not in readme:
        fail(f"README markers {begin} / {end} not found")
    pre, rest = readme.split(begin, 1)
    _, post = rest.split(end, 1)
    sep = " " if inline else "\n"  # inline keeps markdown table cells on one line
    return pre + begin + sep + content + sep + end + post


def fetch_export(dest: Path) -> None:
    """Pull the org-wide OCSF export using a Clerk bearer token (env var)."""
    import os

    token = os.environ.get("AI_IDENTITY_TOKEN")
    if not token:
        fail(
            "--fetch needs AI_IDENTITY_TOKEN set to a Clerk session JWT.\n"
            "  Dashboard tab → devtools console → `await Clerk.session.getToken()`\n"
            "  (tokens expire in ~60s — run this immediately after copying)"
        )
    req = urllib.request.Request(EXPORT_URL, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
    except urllib.error.HTTPError as e:
        fail(f"export fetch failed: HTTP {e.code} — {e.read()[:200]!r} (token expired?)")
    print(f"✓ fetched org-wide export → {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("export_file", nargs="?", help="fresh NDJSON download from format=ocsf")
    ap.add_argument(
        "--fetch", action="store_true", help="download the export first (see docstring)"
    )
    ap.add_argument("--excerpt-seq", default="16-22", help="org_chain_seq range for the excerpt")
    ap.add_argument("--jwks", default=DEFAULT_JWKS_URL, help="JWKS URL or local file")
    ap.add_argument("--bundle-dir", default=str(Path(__file__).parent))
    ap.add_argument("--skip-signatures", action="store_true")
    args = ap.parse_args()

    bundle = Path(args.bundle_dir)
    if args.fetch:
        export_path = Path(args.export_file or (bundle / "fresh-export.download.ndjson"))
        fetch_export(export_path)
    elif args.export_file:
        export_path = Path(args.export_file)
    else:
        ap.error("provide an export file, or --fetch to download one")

    lines = [ln for ln in export_path.read_text().splitlines() if ln.strip()]
    events = [json.loads(ln) for ln in lines]
    if not events:
        fail("export file is empty")

    # 1. Shape
    problems: list[str] = []
    for i, ev in enumerate(events, 1):
        problems.extend(validate_event_shape(ev, i))
    if problems:
        print("\n".join(problems[:40]), file=sys.stderr)
        fail(f"{len(problems)} shape problem(s) — export is not on the final #1661 shape")
    print(f"✓ shape: {len(events)} events, all on final #1661 attestation shape")

    # 2. Chain
    links, first_seq = verify_chain(events)
    print(f"✓ chain: {links} links verified ({first_seq}→{first_seq + len(events) - 1})")

    # 3. Signatures
    if args.skip_signatures:
        print("– signatures: SKIPPED by flag")
    else:
        try:
            import cryptography  # noqa: F401
        except ImportError:
            print("– signatures: SKIPPED (pip install cryptography to enable)", file=sys.stderr)
        else:
            n = verify_signatures(events, load_jwks(args.jwks))
            print(f"✓ signatures: {n}/{len(events)} ECDSA-P256 signatures verified against JWKS")

    # 4. Files
    lo, hi = (int(x) for x in args.excerpt_seq.split("-"))
    excerpt = [ev for ev in events if lo <= ev["unmapped"]["org_chain_seq"] <= hi]
    if len(excerpt) != hi - lo + 1:
        fail(f"excerpt seq {lo}-{hi}: expected {hi - lo + 1} events, found {len(excerpt)}")
    (bundle / "production-ocsf-full-export.ocsf.ndjson").write_text(
        "".join(json.dumps(ev, separators=(",", ":")) + "\n" for ev in events)
    )
    (bundle / "production-ocsf-excerpt.ocsf.ndjson").write_text(
        "".join(json.dumps(ev, separators=(",", ":")) + "\n" for ev in excerpt)
    )
    print(f"✓ wrote full export ({len(events)} events) + excerpt (seq {lo}-{hi})")

    # 5. README injection
    readme_path = bundle / "README.md"
    readme = readme_path.read_text()

    agents = {ev["ai_agent"]["uid"] for ev in events}
    allowed = sum(1 for ev in events if ev.get("action_id") == 1)
    denied = sum(1 for ev in events if ev.get("action_id") == 2)
    last_seq = first_seq + len(events) - 1
    agent_word = "agent" if len(agents) == 1 else "agents"
    stats = (
        f"**Full org chain**, {len(events)} events, seq {first_seq}→{last_seq}, "
        f"{len(agents)} {agent_word} ({allowed} allowed / {denied} denied)"
    )
    readme = inject(readme, STATS_BEGIN, STATS_END, stats, inline=True)

    # Anatomy: the allowed inference inside the excerpt (seq 18 in the
    # canonical slice) — fall back to the first Allowed event in the excerpt.
    anatomy_ev = next(
        (ev for ev in excerpt if ev["unmapped"]["org_chain_seq"] == 18 and ev["action_id"] == 1),
        next(ev for ev in excerpt if ev["action_id"] == 1),
    )
    block = json.dumps(truncate_for_display(anatomy_ev), indent=2, ensure_ascii=False)
    readme = inject(
        readme,
        ANATOMY_BEGIN,
        ANATOMY_END,
        f"```json\n{block}\n```\n*(long hex/base64 values truncated for display — "
        f"the ndjson files carry full values; seq {anatomy_ev['unmapped']['org_chain_seq']})*",
    )
    readme_path.write_text(readme)
    print("✓ README anatomy + stats refreshed from the export")
    print("\nDone. Review `git diff`, then commit + PR to main.")


if __name__ == "__main__":
    main()
