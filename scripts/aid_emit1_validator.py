#!/usr/bin/env python3
"""AID-EMIT-1 conformance validator — "is this a well-formed AID-EMIT-1 record?"

The standalone validator named in ``docs/specs/aid-emit-1.md`` §12. Checks
NDJSON record files against the spec with **nothing but the Python standard
library** — no keys fetched, no packages installed, no network. ECDSA P-256
signature verification is implemented in pure Python so the validator stays
portable (slow but correct; this is a validator, not an ingest path).

What it checks, by spec section:

- **§3/§6 well-formedness** — `metadata.uid` on every chained record;
  `record_integrity` declared in `metadata.profiles` when chaining is on;
  exactly one `attestation_list` entry carrying `uid` / `chain_uid` /
  `fingerprint` (64 lowercase hex, SHA-256/Hex enums, serialization 2 or 99);
  `authority_uid` present whenever the record is signed; `prev_event` with
  `uid` + `fingerprint` (+ `type_uid`, recommended).
- **§4/§11 fingerprint** — reconstructs the covered bytes (strip
  `attestation_list[0].fingerprint` / `.signatures`, strip
  `unmapped.signature_b64` / `signature_key_id`, drop `unmapped` if emptied;
  canonicalize) and recomputes SHA-256. The §4 value-space constraints are
  enforced: a record claiming `serialization_id` 2 (JCS) with non-ASCII keys
  or non-integer numbers is a conformance failure — the claim, not just the
  bytes, must be honest.
- **§5/§11 signature** — with ``--key``, verifies the DER ECDSA-P256
  signature at `unmapped.signature_b64` over the DSSE PAE of the same
  covered bytes, and checks the `digital_signature` descriptor enums
  (algorithm 3 = ECDSA, serialization 5 = DSSE).
- **§6/§7/§11.4 chain** — per `chain_uid`: genesis omits `prev_event`;
  each successor's `prev_event.uid` / `.fingerprint.value` match the
  predecessor's `metadata.uid` / recomputed fingerprint; duplicate
  `metadata.uid` is reported as an idempotent-replay finding; `stream_seq`
  must be dense per `(epoch, stream_id)` — a gap is **surfaced as a
  finding, never repaired** (warning by default, error with
  ``--strict-gaps``); a decrease is an ordering error.

Non-6003 records (e.g. proposed-class drafts using the same
`record_integrity` carrier) get the integrity/chain checks with the
AID-EMIT-1 class-level checks skipped and noted.

Usage:
    python3 aid_emit1_validator.py FILE [FILE ...] [--key PUBKEY.pem]
                                   [--strict-gaps] [--json]
    python3 aid_emit1_validator.py - < records.ndjson

Exit codes: 0 conformant (warnings allowed) · 1 conformance failures ·
2 usage/input error.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field

SPEC = "AID-EMIT-1 v1.0.0-draft (docs/specs/aid-emit-1.md)"
DSSE_PAYLOAD_TYPE = b"application/vnd.ocsf.event+json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# ---------------------------------------------------------------------------
# Canonicalization (§4)
# ---------------------------------------------------------------------------


def value_space_violations(node, path="$"):
    """Yield §4 value-space violations: non-ASCII keys, non-integer numbers."""
    if isinstance(node, dict):
        for k, v in node.items():
            if not k.isascii():
                yield f"non-ASCII key at {path}: {k!r}"
            yield from value_space_violations(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from value_space_violations(v, f"{path}[{i}]")
    elif isinstance(node, float):
        yield f"non-integer number at {path}: {node!r}"


def canonical_bytes(obj) -> bytes:
    """RFC 8785 canonical form for the §4-constrained value space.

    For ASCII keys (byte order == UTF-16 code-unit order) and integer
    numbers, sorted-keys compact JSON is byte-identical to full JCS — the
    same equivalence the reference emitter relies on.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def covered_bytes(event: dict) -> bytes:
    """§4: the bytes the fingerprint and signature cover, from an emitted record."""
    ev = copy.deepcopy(event)
    atts = ev.get("attestation_list")
    if isinstance(atts, list) and atts and isinstance(atts[0], dict):
        atts[0].pop("fingerprint", None)
        atts[0].pop("signatures", None)
    un = ev.get("unmapped")
    if isinstance(un, dict):
        un.pop("signature_b64", None)
        un.pop("signature_key_id", None)
        if not un:
            ev.pop("unmapped", None)
    return canonical_bytes(ev)


def dsse_pae(payload: bytes) -> bytes:
    """§5: DSSE Pre-Authentication Encoding over the covered bytes."""
    t = DSSE_PAYLOAD_TYPE
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


# ---------------------------------------------------------------------------
# Pure-Python ECDSA P-256 verification (§5) — stdlib only, by design.
# ---------------------------------------------------------------------------

P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = P - 3
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5

_INF = None  # point at infinity


def _on_curve(pt) -> bool:
    if pt is _INF:
        return True
    x, y = pt
    return (y * y - (x * x * x + A * x + B)) % P == 0


def _pt_add(p1, p2):
    if p1 is _INF:
        return p2
    if p2 is _INF:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return _INF
    if p1 == p2:
        lam = (3 * x1 * x1 + A) * pow(2 * y1, -1, P) % P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def _pt_mul(k: int, pt):
    acc = _INF
    addend = pt
    while k:
        if k & 1:
            acc = _pt_add(acc, addend)
        addend = _pt_add(addend, addend)
        k >>= 1
    return acc


# --- minimal DER (TLV) parsing: just enough for SPKI and ECDSA-Sig ---------


def _der_read(data: bytes, off: int):
    """Return (tag, value, next_offset). Raises ValueError on malformed DER."""
    if off + 2 > len(data):
        raise ValueError("truncated DER")
    tag = data[off]
    length = data[off + 1]
    off += 2
    if length & 0x80:
        nbytes = length & 0x7F
        if nbytes == 0 or off + nbytes > len(data):
            raise ValueError("bad DER length")
        length = int.from_bytes(data[off : off + nbytes], "big")
        off += nbytes
    if off + length > len(data):
        raise ValueError("truncated DER value")
    return tag, data[off : off + length], off + length


_OID_EC_PUBLIC_KEY = bytes.fromhex("2a8648ce3d0201")  # 1.2.840.10045.2.1
_OID_PRIME256V1 = bytes.fromhex("2a8648ce3d030107")  # 1.2.840.10045.3.1.7


def load_p256_public_key(pem: str):
    """Parse a PEM SubjectPublicKeyInfo into an affine P-256 point."""
    m = re.search(r"-----BEGIN PUBLIC KEY-----(.*?)-----END PUBLIC KEY-----", pem, re.S)
    if not m:
        raise ValueError("not a PEM SubjectPublicKeyInfo (-----BEGIN PUBLIC KEY-----)")
    der = base64.b64decode("".join(m.group(1).split()))
    tag, spki, _ = _der_read(der, 0)
    if tag != 0x30:
        raise ValueError("SPKI: expected outer SEQUENCE")
    tag, alg, off = _der_read(spki, 0)
    if tag != 0x30:
        raise ValueError("SPKI: expected AlgorithmIdentifier SEQUENCE")
    t1, oid1, aoff = _der_read(alg, 0)
    t2, oid2, _ = _der_read(alg, aoff)
    if t1 != 0x06 or oid1 != _OID_EC_PUBLIC_KEY:
        raise ValueError("SPKI: not an EC public key")
    if t2 != 0x06 or oid2 != _OID_PRIME256V1:
        raise ValueError("SPKI: curve is not prime256v1 (P-256)")
    tag, bits, _ = _der_read(spki, off)
    if tag != 0x03 or len(bits) != 1 + 65 or bits[0] != 0 or bits[1] != 0x04:
        raise ValueError("SPKI: expected uncompressed P-256 point")
    x = int.from_bytes(bits[2:34], "big")
    y = int.from_bytes(bits[34:66], "big")
    pt = (x, y)
    if not _on_curve(pt):
        raise ValueError("public key point is not on P-256")
    return pt


def parse_der_signature(sig: bytes) -> tuple[int, int]:
    tag, seq, _ = _der_read(sig, 0)
    if tag != 0x30:
        raise ValueError("signature: expected DER SEQUENCE")
    t1, rb, off = _der_read(seq, 0)
    t2, sb, _ = _der_read(seq, off)
    if t1 != 0x02 or t2 != 0x02:
        raise ValueError("signature: expected two DER INTEGERs")
    return int.from_bytes(rb, "big"), int.from_bytes(sb, "big")


def ecdsa_p256_sha256_verify(pubkey, message: bytes, der_signature: bytes) -> bool:
    try:
        r, s = parse_der_signature(der_signature)
    except ValueError:
        return False
    if not (1 <= r < N and 1 <= s < N):
        return False
    e = int.from_bytes(hashlib.sha256(message).digest(), "big")
    w = pow(s, -1, N)
    u1 = (e * w) % N
    u2 = (r * w) % N
    pt = _pt_add(_pt_mul(u1, (GX, GY)), _pt_mul(u2, pubkey))
    if pt is _INF:
        return False
    return pt[0] % N == r


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


@dataclass
class Findings:
    items: list = field(default_factory=list)

    def add(self, level: str, code: str, record: int | None, message: str) -> None:
        self.items.append({"level": level, "code": code, "record": record, "message": message})

    def error(self, code, record, message):
        self.add("ERROR", code, record, message)

    def warn(self, code, record, message):
        self.add("WARN", code, record, message)

    def info(self, code, record, message):
        self.add("INFO", code, record, message)

    @property
    def failed(self) -> bool:
        return any(f["level"] == "ERROR" for f in self.items)


# ---------------------------------------------------------------------------
# Record-level checks (§3, §4, §5, §6)
# ---------------------------------------------------------------------------


def check_record(ev: dict, idx: int, out: Findings, pubkey=None) -> str | None:
    """Validate one record; return its recomputed fingerprint (hex) or None."""
    atts = ev.get("attestation_list")
    chained = isinstance(atts, list) and len(atts) > 0

    metadata = ev.get("metadata")
    if not isinstance(metadata, dict):
        out.error("E-META", idx, "metadata object missing")
        metadata = {}

    if ev.get("class_uid") != 6003:
        out.warn(
            "W-CLASS",
            idx,
            f"class_uid {ev.get('class_uid')!r} is not API Activity (6003); "
            "AID-EMIT-1 class checks skipped, integrity checks still applied",
        )
    elif chained and "record_integrity" not in (metadata.get("profiles") or []):
        out.error(
            "E-PROFILE",
            idx,
            "chained record does not declare 'record_integrity' in metadata.profiles (§3)",
        )

    if not chained:
        out.warn(
            "W-UNCHAINED", idx, "no attestation_list: record is not chained; nothing to verify"
        )
        return None
    if len(atts) != 1:
        out.error(
            "E-ATT-COUNT", idx, f"expected exactly one attestation entry, found {len(atts)} (§6)"
        )
    att = atts[0] if isinstance(atts[0], dict) else {}

    if not metadata.get("uid"):
        out.error("E-UID", idx, "metadata.uid missing on a chained record (§6)")
    for req in ("uid", "chain_uid"):
        if not att.get(req):
            out.error("E-ATT-FIELD", idx, f"attestation_list[0].{req} missing (§6)")

    signed = isinstance(ev.get("unmapped"), dict) and "signature_b64" in ev["unmapped"]
    if signed and not att.get("authority_uid"):
        out.error("E-AUTHORITY", idx, "signed record without attestation authority_uid (§6)")

    fp = att.get("fingerprint")
    sigs = att.get("signatures")
    if not fp and not sigs:
        out.error("E-AT-LEAST-ONE", idx, "attestation has neither fingerprint nor signatures")
        return None

    recomputed = None
    if isinstance(fp, dict):
        value = fp.get("value", "")
        if not HEX64.match(value or ""):
            out.error("E-FP-FORM", idx, "fingerprint.value is not 64 lowercase hex (§4)")
        if fp.get("algorithm_id") != 3:
            out.error(
                "E-FP-ALG",
                idx,
                f"fingerprint.algorithm_id {fp.get('algorithm_id')!r} != 3 (SHA-256)",
            )
        if fp.get("encoding_id") != 1:
            out.error(
                "E-FP-ENC", idx, f"fingerprint.encoding_id {fp.get('encoding_id')!r} != 1 (Hex)"
            )
        ser = fp.get("serialization_id")
        if ser not in (2, 99):
            out.error(
                "E-FP-SER",
                idx,
                f"fingerprint.serialization_id {ser!r} not in (2 JCS, 99 Other) (§4)",
            )
        elif ser == 99 and not fp.get("serialization"):
            out.warn(
                "W-FP-SER99", idx, "serialization_id 99 without a sibling naming the scheme (§4)"
            )

        violations = list(value_space_violations(ev))
        if violations and ser == 2:
            for v in violations[:5]:
                out.error(
                    "E-JCS-SPACE",
                    idx,
                    f"serialization_id 2 claimed but value space violates §4: {v}",
                )

        recomputed = hashlib.sha256(covered_bytes(ev)).hexdigest()
        if value and HEX64.match(value) and recomputed != value:
            scheme = "JCS" if ser == 2 else f"scheme {fp.get('serialization')!r}"
            out.error(
                "E-FP-MISMATCH",
                idx,
                f"fingerprint does not reproduce under §4 covered bytes ({scheme}): "
                f"claimed {value[:16]}…, computed {recomputed[:16]}…",
            )

    if signed:
        descriptor = (sigs or [{}])[0] if isinstance(sigs, list) and sigs else {}
        if not descriptor:
            out.error(
                "E-SIG-DESC", idx, "signed record without a digital_signature descriptor (§5)"
            )
        else:
            if descriptor.get("algorithm_id") != 3:
                out.error("E-SIG-ALG", idx, "digital_signature.algorithm_id != 3 (ECDSA) (§5)")
            if descriptor.get("serialization_id") != 5:
                out.error("E-SIG-SER", idx, "digital_signature.serialization_id != 5 (DSSE) (§5)")
        if "signature_key_id" not in ev["unmapped"]:
            out.warn("W-SIG-KID", idx, "signature present without unmapped.signature_key_id (§5)")
        if pubkey is not None:
            try:
                der = base64.b64decode(ev["unmapped"]["signature_b64"], validate=True)
            except (binascii.Error, ValueError):
                out.error("E-SIG-B64", idx, "unmapped.signature_b64 is not valid base64")
            else:
                if ecdsa_p256_sha256_verify(pubkey, dsse_pae(covered_bytes(ev)), der):
                    out.info(
                        "I-SIG-OK", idx, "DSSE ECDSA-P256 signature verifies over §4 covered bytes"
                    )
                else:
                    out.error(
                        "E-SIG-VERIFY",
                        idx,
                        "signature does not verify over the DSSE PAE of the covered bytes (§11)",
                    )
        else:
            out.info("I-SIG-SKIP", idx, "signature present; no --key given, verification skipped")

    return recomputed


# ---------------------------------------------------------------------------
# Chain-level checks (§6, §7, §11 step 4)
# ---------------------------------------------------------------------------


def check_chains(
    events: list[dict], fingerprints: list[str | None], out: Findings, strict_gaps: bool
) -> None:
    heads: dict[str, tuple[str, str | None]] = {}  # chain_uid -> (last uid, last fp)
    seen_uids: dict[str, set] = {}
    streams: dict[
        tuple, list[tuple[int, int]]
    ] = {}  # (chain, epoch, stream_id) -> [(seq, record#)]

    for idx, (ev, fp) in enumerate(zip(events, fingerprints, strict=True), start=1):
        atts = ev.get("attestation_list")
        if not (isinstance(atts, list) and atts and isinstance(atts[0], dict)):
            continue
        att = atts[0]
        chain = att.get("chain_uid")
        uid = (ev.get("metadata") or {}).get("uid")
        if not chain:
            continue

        chain_seen = seen_uids.setdefault(chain, set())
        if uid and uid in chain_seen:
            out.warn(
                "W-DUP-UID",
                idx,
                f"duplicate metadata.uid {uid!r} in chain (idempotent replay?); not advancing chain",
            )
            continue
        if uid:
            chain_seen.add(uid)

        pe = att.get("prev_event")
        if chain not in heads:
            if pe is not None:
                out.warn(
                    "W-CHAIN-HEAD",
                    idx,
                    "first record of chain in input carries prev_event; chain head not in input, linkage unverifiable here",
                )
        elif pe is None:
            out.error("E-GENESIS", idx, "non-genesis record omits prev_event (§6)")
        else:
            prev_uid, prev_fp = heads[chain]
            if (
                not isinstance(pe, dict)
                or not pe.get("uid")
                or not isinstance(pe.get("fingerprint"), dict)
            ):
                out.error("E-PREV-FORM", idx, "prev_event missing uid or fingerprint object (§6)")
            else:
                if "type_uid" not in pe:
                    out.warn("W-PREV-TYPE", idx, "prev_event.type_uid missing (§6 lists it)")
                if pe["uid"] != prev_uid:
                    out.error(
                        "E-CHAIN-UID",
                        idx,
                        f"prev_event.uid {pe['uid']!r} != predecessor metadata.uid {prev_uid!r} (§11)",
                    )
                if prev_fp and pe["fingerprint"].get("value") != prev_fp:
                    out.error(
                        "E-CHAIN-FP",
                        idx,
                        "prev_event.fingerprint does not match predecessor's recomputed fingerprint (§11)",
                    )
        heads[chain] = (uid, fp)

        stream = (ev.get("unmapped") or {}).get("cpex.stream")
        if isinstance(stream, dict) and stream.get("stream_seq") is not None:
            key = (chain, stream.get("epoch"), stream.get("stream_id"))
            streams.setdefault(key, []).append((stream["stream_seq"], idx))

    for (_chain, epoch, stream_id), entries in streams.items():
        prev_seq = None
        for seq, idx in entries:
            if prev_seq is not None:
                if seq <= prev_seq:
                    out.error(
                        "E-STREAM-ORDER",
                        idx,
                        f"stream_seq {seq} not increasing after {prev_seq} in ({epoch}, {stream_id!r}) (§7)",
                    )
                elif seq != prev_seq + 1:
                    level = out.error if strict_gaps else out.warn
                    level(
                        "GAP-STREAM",
                        idx,
                        f"stream_seq gap in ({epoch}, {stream_id!r}): expected {prev_seq + 1}, got {seq} — "
                        "a gap is evidence to surface, not repair (§7)",
                    )
            prev_seq = seq


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def validate_stream(lines, out: Findings, pubkey=None, strict_gaps=False) -> int:
    events = []
    for lineno, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as exc:
            out.error("E-JSON", lineno, f"line {lineno}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(ev, dict):
            out.error("E-JSON", lineno, f"line {lineno}: not a JSON object")
            continue
        events.append(ev)

    fingerprints = [check_record(ev, i, out, pubkey) for i, ev in enumerate(events, start=1)]
    check_chains(events, fingerprints, out, strict_gaps)
    return len(events)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Validate NDJSON records against {SPEC}.")
    parser.add_argument("files", nargs="+", help="NDJSON record files ('-' for stdin)")
    parser.add_argument(
        "--key", help="PEM P-256 public key for signature verification (§11 step 3)"
    )
    parser.add_argument(
        "--strict-gaps", action="store_true", help="treat stream_seq gaps as errors (CI mode)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable findings on stdout")
    args = parser.parse_args(argv)

    pubkey = None
    if args.key:
        try:
            with open(args.key, encoding="utf-8") as fh:
                pubkey = load_p256_public_key(fh.read())
        except (OSError, ValueError) as exc:
            print(f"error: cannot load public key: {exc}", file=sys.stderr)
            return 2

    out = Findings()
    total = 0
    for path in args.files:
        try:
            if path == "-":
                total += validate_stream(sys.stdin, out, pubkey, args.strict_gaps)
            else:
                with open(path, encoding="utf-8") as fh:
                    total += validate_stream(fh, out, pubkey, args.strict_gaps)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if args.json:
        print(
            json.dumps(
                {"spec": SPEC, "records": total, "pass": not out.failed, "findings": out.items},
                indent=2,
            )
        )
    else:
        for f in out.items:
            where = f"record {f['record']}" if f["record"] else "input"
            print(f"{f['level']:5} {f['code']:15} {where}: {f['message']}")
        errors = sum(1 for f in out.items if f["level"] == "ERROR")
        warns = sum(1 for f in out.items if f["level"] == "WARN")
        verdict = "FAIL" if out.failed else "PASS"
        print(f"{verdict}: {total} records — {errors} errors, {warns} warnings ({SPEC})")

    return 1 if out.failed else 0


if __name__ == "__main__":
    sys.exit(main())
