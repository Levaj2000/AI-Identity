#!/usr/bin/env python3
"""Offline verifier for the sample OCSF ``attestation_finding`` (PR #1689).

Self-contained: Python 3.10+ and the ``cryptography`` package. It deliberately
re-implements RFC 6962 hashing and DSSE PAE in-file (~30 lines) rather than
importing anything from the producer — an attestation a third party cannot
independently verify is not an attestation.

    python3 verify_finding.py                      # verify both finding variants
    python3 verify_finding.py --tamper substitute  # edit one referenced event (self-consistent forgery)
    python3 verify_finding.py --tamper delete      # drop one referenced event
    python3 verify_finding.py --prove 3            # O(log N) inclusion proof for reference #3

What each variant of the finding lets a verifier check:

  as-1689 (refs = uid/type_uid only)   existence & count of referenced events
  with-hashes (refs + record_hash)     the above, PLUS: each reference is bound
                                       to record content, and the Merkle root
                                       recomputed from the references matches
                                       the signed checkpoint

The demo point: DELETING a referenced event is caught by both variants;
EDITING/substituting one is invisible to uid-only references and caught,
with the exact position, once each reference carries a hash.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

HERE = Path(__file__).resolve().parent
CHECKPOINT_PAYLOAD_TYPE = "application/vnd.ai-identity.anchor-checkpoint+json"

OK, MISS, CAUGHT, NA = "PASS", "MISSED (verifies falsely)", "TAMPER DETECTED", "not checkable"


# ---- RFC 6962 (Certificate Transparency) hashing, re-implemented locally ----


def leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root(leaves: list[bytes]) -> bytes:
    hs = [leaf_hash(d) for d in leaves]

    def root(h: list[bytes]) -> bytes:
        if len(h) == 1:
            return h[0]
        k = 1
        while k * 2 < len(h):
            k *= 2
        return node_hash(root(h[:k]), root(h[k:]))

    return root(hs)


def verify_inclusion(
    leaf_data: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes
) -> bool:
    """RFC 6962 §2.1.1 inclusion-proof verification, verbatim."""
    if tree_size <= 0 or not 0 <= index < tree_size:
        return False
    fn, sn, r = index, tree_size - 1, leaf_hash(leaf_data)
    for p in proof:
        if sn == 0:
            return False
        if (fn & 1) or fn == sn:
            r = node_hash(p, r)
            if not (fn & 1):
                while True:
                    fn >>= 1
                    sn >>= 1
                    if fn & 1 or fn == 0:
                        break
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


# ---- DSSE (dead simple signing envelope) verification ----


def pae(payload_type: str, payload: bytes) -> bytes:
    return b"DSSEv1 %d %s %d %s" % (len(payload_type), payload_type.encode(), len(payload), payload)


def verify_checkpoint(envelope: dict, public_key_pem: bytes) -> dict:
    """Return the signed checkpoint payload iff the DSSE signature verifies."""
    if envelope["payloadType"] != CHECKPOINT_PAYLOAD_TYPE:
        raise SystemExit(f"unexpected payloadType {envelope['payloadType']!r}")
    payload = base64.b64decode(envelope["payload"])
    sig = base64.b64decode(envelope["signatures"][0]["sig"])
    key = serialization.load_pem_public_key(public_key_pem)
    try:
        key.verify(sig, pae(CHECKPOINT_PAYLOAD_TYPE, payload), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        raise SystemExit("checkpoint DSSE signature INVALID") from None
    return json.loads(payload)


# ---- the finding-level checks ----


def check_finding(
    finding: dict, events_by_uid: dict[str, dict], checkpoint: dict
) -> tuple[str, list[str]]:
    """Run every check the finding's reference shape permits. Returns (verdict, log)."""
    log: list[str] = []
    refs = finding["finding_info"]["related_events"]
    signed_root = checkpoint["merkle_root"]

    att_digest = finding["attestation_list"][0]["signatures"][0]["digest"]["value"]
    log.append(
        f"signed root matches attestation_list digest: {'yes' if att_digest == signed_root else 'NO'}"
    )
    if att_digest != signed_root:
        return CAUGHT, log

    # Check 1 — existence & count (all any uid-only reference can support).
    missing = [r["uid"] for r in refs if r["uid"] not in events_by_uid]
    if missing:
        log.append(f"reference resolution: event uid(s) {missing} MISSING")
        return CAUGHT, log
    log.append(f"reference resolution: {len(refs)}/{len(refs)} events present")
    if len(refs) != checkpoint["tree_size"]:
        log.append(f"count vs signed tree_size: {len(refs)} != {checkpoint['tree_size']}")
        return CAUGHT, log
    log.append(f"count vs signed tree_size: {len(refs)} == {checkpoint['tree_size']}")

    # Check 2 — content binding, only possible when references carry a hash.
    if not all("record_hash" in r for r in refs):
        log.append("record content binding: no hash in references -> " + NA)
        log.append("merkle root recomputation: no leaves available -> " + NA)
        return OK, log  # everything CHECKABLE passed; edits are invisible here

    mismatches = [
        i
        for i, r in enumerate(refs)
        if events_by_uid[r["uid"]]["attestation"]["entry_hash"]["value"]
        != r["record_hash"]["value"]
    ]
    if mismatches:
        log.append(f"record content binding: hash mismatch at reference index {mismatches}")
        return CAUGHT, log
    log.append("record content binding: all reference hashes match presented records")

    recomputed = merkle_root([bytes.fromhex(r["record_hash"]["value"]) for r in refs]).hex()
    if recomputed != signed_root:
        log.append(f"merkle root recomputation: {recomputed[:16]}… != signed {signed_root[:16]}…")
        return CAUGHT, log
    log.append("merkle root recomputation: matches the signed checkpoint root")
    return OK, log


def tamper(events: list[dict], mode: str) -> tuple[list[dict], str]:
    events = copy.deepcopy(events)
    victim = len(events) // 2
    uid = events[victim]["attestation"]["uid"]
    if mode == "delete":
        del events[victim]
        return events, f"deleted event uid={uid}"
    # substitute: a SELF-CONSISTENT forgery — content edited AND the record's
    # own hash + signature digest rewritten to match the forged content, the
    # strongest tamper an attacker with storage access can perform.
    e = events[victim]
    e["api"]["operation"] = "/api/v1/briefings/FORGED"
    forged = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
    e["attestation"]["entry_hash"]["value"] = forged
    for s in e["attestation"].get("signatures", []):
        s["digest"]["value"] = forged
    return (
        events,
        f"substituted event uid={uid} (content + its recorded hash rewritten consistently)",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tamper", choices=["substitute", "delete"])
    ap.add_argument(
        "--prove", type=int, metavar="N", help="verify inclusion proof for reference #N"
    )
    args = ap.parse_args()

    events = [
        json.loads(ln) for ln in (HERE / "source-events.ocsf.ndjson").read_text().splitlines() if ln
    ]
    pub_pem = (HERE / "checkpoint-public-key.pem").read_bytes()
    envelope = json.loads((HERE / "evidence-anchor-checkpoint.dsse.json").read_text())

    checkpoint = verify_checkpoint(envelope, pub_pem)
    print("[checkpoint] DSSE signature: valid (ECDSA-P256, public key only)")
    print(
        f"[checkpoint] committed: {checkpoint['tree_size']} events, root {checkpoint['merkle_root'][:16]}…\n"
    )

    if args.prove is not None:
        proofs = json.loads((HERE / "inclusion-proofs.json").read_text())
        p = proofs["proofs"][args.prove]
        ok = verify_inclusion(
            bytes.fromhex(p["entry_hash"]),
            p["ref_index"],
            proofs["tree_size"],
            [bytes.fromhex(x) for x in p["audit_path"]],
            bytes.fromhex(checkpoint["merkle_root"]),
        )
        print(
            f"[inclusion] reference #{args.prove} (event uid={p['event_uid']}): "
            f"{'PROVEN in signed checkpoint' if ok else 'PROOF FAILED'} "
            f"({len(p['audit_path'])} path steps, O(log N))"
        )
        return

    note = ""
    if args.tamper:
        events, note = tamper(events, args.tamper)
        print(f"[tamper] {note}\n")
    events_by_uid = {e["attestation"]["uid"]: e for e in events}

    for name in ("attestation-finding.as-1689.json", "attestation-finding.with-hashes.json"):
        finding = json.loads((HERE / name).read_text())
        verdict, log = check_finding(finding, events_by_uid, checkpoint)
        shape = "refs: uid/type_uid only" if "as-1689" in name else "refs: + record_hash"
        headline = verdict if not (args.tamper and verdict == OK) else MISS
        print(f"=== {name}  ({shape})")
        for line in log:
            print(f"    {line}")
        print(f"    VERDICT: {headline}\n")


if __name__ == "__main__":
    main()
