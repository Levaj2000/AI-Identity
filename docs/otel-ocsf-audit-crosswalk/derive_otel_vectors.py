#!/usr/bin/env python3
"""Derive OTel AuditRecord test vectors from the OCSF reference bundle.

Applies the crosswalk in README.md mechanically: reads OCSF API Activity
events (class 6003, ``ai_operation`` + ``record_integrity`` profiles, the
final #1661 attestation shape) and emits one OTel ``AuditRecord`` per event,
shaped per the apeirora audit data model (``specification/audit/data-model.md``,
``auditing`` branch). Stdlib only — no OTel SDK, no crypto dependencies.

Each output line is a self-contained JSON object carrying ``Resource`` +
LogRecord fields + ``Attributes``. In real OTLP the Resource would be the
batch envelope, not repeated per record; the per-line shape here is for
fixture ergonomics (NDJSON, SIEM-style).

After deriving, the script re-verifies chain linkage *across the transform*:
for consecutive ``audit.sequence.number`` values in the same
``audit.sequence.stream_id``, record N+1's ``audit.sequence.prev_hash`` must
equal record N's ``ocsf.attestation.entry_hash``. A transform that breaks
this check has corrupted the integrity constructs it claims to preserve.

ECDSA signature verification is deliberately out of scope here (not in the
stdlib): use the bundle's ``regenerate.py`` on the OCSF side, or follow the
recipe in README.md §3 — the signatures survive this transform byte-for-byte
and verify against the same public JWKS.

Usage:
    python3 derive_otel_vectors.py                       # excerpt -> sample
    python3 derive_otel_vectors.py --full                # full export
    python3 derive_otel_vectors.py IN.ndjson -o OUT.ndjson
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BUNDLE_DIR = (
    Path(__file__).resolve().parent.parent / "cosai-ws4-ocsf-mapping" / "ocsf-log-reference-bundle"
)
DEFAULT_INPUT = BUNDLE_DIR / "production-ocsf-excerpt.ocsf.ndjson"
FULL_INPUT = BUNDLE_DIR / "production-ocsf-full-export.ocsf.ndjson"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "otel-audit-records.sample.ndjson"

# API Activity (6003) activity axis -> OTel EventName / audit.action verb.
ACTIVITY_VERBS = {1: "create", 2: "read", 3: "update", 4: "delete"}

# OCSF actor.user.type_id -> audit.actor.type.
ACTOR_TYPES = {1: "user", 2: "user", 3: "service"}  # 1 User, 2 Admin, 3 System/service

# OCSF disposition/action axis -> audit.outcome. The policy decision itself
# is preserved separately as ocsf.action / ocsf.action_id (README §2.6).
OUTCOMES = {1: "success", 2: "failure"}

# signatures[].algorithm (OCSF string) -> JWA identifier for
# audit.integrity.algorithm (README §2.7).
JWA_ALGORITHMS = {
    "ECDSA-P256-SHA256": "ES256",
    "ECDSA-P384-SHA384": "ES384",
    "RSA-SHA256": "RS256",
    "Ed25519": "EdDSA",
}


def pick_attestation(event: dict) -> dict | None:
    """The record-integrity attestation entry (single-attester producer)."""
    lst = event.get("attestation_list") or []
    return lst[0] if lst else None


def ocsf_to_otel(event: dict) -> dict:
    """Map one OCSF 6003 event to one OTel AuditRecord (README §1)."""
    att = pick_attestation(event)
    unmapped = event.get("unmapped", {})
    activity = ACTIVITY_VERBS.get(event.get("activity_id"), "other")
    actor_user = (event.get("actor") or {}).get("user") or {}
    agent = event.get("ai_agent") or {}
    http = event.get("http_request") or {}

    attrs: dict = {
        # --- mandatory audit.* -------------------------------------------
        "audit.record.id": event["metadata"]["uid"],
        "audit.actor.id": actor_user.get("uid", "unknown"),
        "audit.actor.type": ACTOR_TYPES.get(actor_user.get("type_id"), "service"),
        "audit.action": activity.upper(),
        "audit.outcome": OUTCOMES.get(event.get("action_id"), "unknown"),
        # --- optional audit.* --------------------------------------------
        "audit.target.id": event.get("api", {}).get("operation"),
        "audit.target.type": "http.endpoint",
        "audit.schema.version": f"ocsf/{event['metadata']['version']}",
    }

    if att:
        if att.get("chain_uid"):
            attrs["audit.sequence.stream_id"] = att["chain_uid"]
        if unmapped.get("org_chain_seq") is not None:
            attrs["audit.sequence.number"] = unmapped["org_chain_seq"]
        prev = att.get("prev_event")
        if prev:
            # Genesis records omit prev_event entirely on the OCSF side and
            # therefore omit audit.sequence.prev_hash here — a deliberate,
            # documented divergence from the data model's SHA-256("")
            # genesis constant (README §2.3).
            attrs["audit.sequence.prev_hash"] = prev["fingerprint"]["value"]
            attrs["ocsf.attestation.prev_event.uid"] = prev["uid"]

        # The signature bytes ride unmapped on the OCSF side (digital_signature
        # has no bytes field — ocsf-schema#1709); on the OTel side they ARE the
        # integrity proof.
        if unmapped.get("signature_b64"):
            attrs["audit.integrity.value"] = unmapped["signature_b64"]
            attrs["audit.integrity.signer"] = "producer"

        # Origin-shape integrity facts a verifier needs post-transform
        # (README §2.1): the signature is computed over
        # bytes.fromhex(entry_hash), NOT over JCS of this record.
        fp = att.get("fingerprint")
        if fp:
            attrs["ocsf.attestation.entry_hash"] = fp["value"]
            attrs["ocsf.attestation.entry_hash.algorithm"] = fp["algorithm"]
            attrs["ocsf.attestation.canonicalization"] = fp["serialization"]

    # --- lossless remainder: fields OTel audit.* has no home for ---------
    if agent.get("uid"):
        attrs["gen_ai.agent.id"] = agent["uid"]
    if agent.get("name"):
        attrs["gen_ai.agent.name"] = agent["name"]
    if http.get("http_method"):
        attrs["http.request.method"] = http["http_method"]
    if (http.get("url") or {}).get("path"):
        attrs["url.path"] = http["url"]["path"]
    attrs["ocsf.class_uid"] = event["class_uid"]
    attrs["ocsf.type_uid"] = event["type_uid"]
    attrs["ocsf.action"] = event.get("action")
    attrs["ocsf.action_id"] = event.get("action_id")
    if event.get("duration") is not None:
        attrs["ocsf.duration_ms"] = event["duration"]
    if unmapped.get("policy_version") is not None:
        attrs["ocsf.policy_version"] = unmapped["policy_version"]

    record = {
        "Timestamp": event["time"] * 1_000_000,  # OCSF ms -> OTel ns
        # The OCSF record carries no SDK-observation time (metadata.logged_time
        # is not emitted by this producer); constraint says
        # ObservedTimestamp >= Timestamp, so equality is the honest floor.
        "ObservedTimestamp": event["time"] * 1_000_000,
        "EventName": f"api.activity.{activity}",
        "Body": None,
        "Attributes": {k: v for k, v in attrs.items() if v is not None},
    }
    return record


def derive(in_path: Path, out_path: Path) -> int:
    events = [json.loads(line) for line in in_path.open() if line.strip()]

    # Resource-level integrity attributes (README §2.7): the data model pins
    # algorithm + key reference at Resource scope, once per service instance.
    # Verify the fixture actually satisfies that before claiming it.
    kids = {
        e["unmapped"]["signature_key_id"]
        for e in events
        if e.get("unmapped", {}).get("signature_key_id")
    }
    algs = {
        s["algorithm"]
        for e in events
        for a in e.get("attestation_list", [])
        for s in a.get("signatures", [])
    }
    if len(kids) > 1 or len(algs) > 1:
        sys.exit(
            f"ERROR: multiple signing keys ({len(kids)}) or algorithms ({algs}) in one export — "
            "cannot be represented as Resource-level audit.integrity.* (README §2.7)."
        )
    resource = {"service.name": "ai-identity-gateway"}
    if algs:
        alg = algs.pop()
        resource["audit.integrity.algorithm"] = JWA_ALGORITHMS.get(alg, alg)
    if kids:
        resource["audit.integrity.certificate"] = kids.pop()

    records = []
    for event in events:
        rec = ocsf_to_otel(event)
        rec = {"Resource": resource, **rec}
        records.append(rec)

    with out_path.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")

    # -- post-transform chain verification --------------------------------
    by_stream: dict[str, list[dict]] = {}
    for rec in records:
        sid = rec["Attributes"].get("audit.sequence.stream_id")
        if sid:
            by_stream.setdefault(sid, []).append(rec)

    links_ok = links_bad = links_skipped = 0
    for sid, recs in by_stream.items():
        recs.sort(key=lambda r: r["Attributes"].get("audit.sequence.number", 0))
        for prev_rec, rec in zip(recs, recs[1:], strict=False):  # pairwise; lengths differ by one
            a, pa = rec["Attributes"], prev_rec["Attributes"]
            if a.get("audit.sequence.number") != pa.get("audit.sequence.number", -2) + 1:
                links_skipped += 1  # non-consecutive slice; predecessor not in this file
                continue
            if a.get("audit.sequence.prev_hash") == pa.get("ocsf.attestation.entry_hash"):
                links_ok += 1
            else:
                links_bad += 1
                print(
                    f"LINK BROKEN: stream {sid} seq {a.get('audit.sequence.number')}",
                    file=sys.stderr,
                )

    genesis = sum(
        1
        for r in records
        if r["Attributes"].get("audit.sequence.number") == 1
        and "audit.sequence.prev_hash" not in r["Attributes"]
    )
    print(f"{len(records)} AuditRecords -> {out_path.name}")
    print(
        f"chain linkage across the transform: {links_ok} verified, {links_bad} broken, "
        f"{links_skipped} skipped (predecessor outside this file)"
    )
    if genesis:
        print(f"genesis records: {genesis} (prev_hash omitted — see README §2.3)")
    return 1 if links_bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument(
        "--full",
        action="store_true",
        help="derive from the full 236-event production export instead of the excerpt",
    )
    args = ap.parse_args()
    in_path = FULL_INPUT if args.full else args.input
    out_path = args.output or (
        Path(__file__).resolve().parent / "otel-audit-records.full.ndjson"
        if args.full
        else DEFAULT_OUTPUT
    )
    return derive(in_path, out_path)


if __name__ == "__main__":
    sys.exit(main())
