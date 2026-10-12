"""Re-derive the AID-EMIT-1 dispatch vector in Python and compare byte for byte.

Feasibility check for the Python emitter design (docs/specs/aid-emit-py.md):
for every signed record in integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md,
recompute the covered bytes (AID-EMIT-1 section 4), the SHA-256 fingerprint,
and the RFC 6979 deterministic ECDSA P-256 signature over the DSSE PAE
(section 5), using the demo scalar emit_sample.rs generates at runtime
(0x42 repeated 32 times; a demo key, never a real credential).

    python3 scripts/aid_emit_py_vector_check.py \
        integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md

Exits 0 when every fingerprint and signature is byte-identical to the vector.
Needs the `cryptography` package, version 44 or later (deterministic_signing).
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

PAYLOAD_TYPE = b"application/vnd.ocsf.event+json"
DEMO_SCALAR = int.from_bytes(b"\x42" * 32, "big")


def signed_records(markdown: str) -> list[dict]:
    """JSON objects in the file that carry an attestation_list."""
    records, buf, depth = [], [], 0
    for line in markdown.splitlines():
        if depth == 0 and line.startswith("{"):
            buf = []
        if depth or line.startswith("{"):
            buf.append(line)
            depth += line.count("{") - line.count("}")
            if depth == 0:
                try:
                    record = json.loads("\n".join(buf))
                except ValueError:
                    continue
                if isinstance(record, dict) and "attestation_list" in record:
                    records.append(record)
    return records


def covered_bytes(record: dict) -> bytes:
    """AID-EMIT-1 section 4: strip the envelope, then canonicalize."""
    ev = copy.deepcopy(record)
    att = ev["attestation_list"][0]
    att.pop("fingerprint", None)
    att.pop("signatures", None)
    unmapped = ev.get("unmapped", {})
    unmapped.pop("signature_b64", None)
    unmapped.pop("signature_key_id", None)
    if "unmapped" in ev and not unmapped:
        del ev["unmapped"]
    return json.dumps(ev, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def dsse_pae(payload: bytes) -> bytes:
    return b"DSSEv1 %d %s %d %s" % (len(PAYLOAD_TYPE), PAYLOAD_TYPE, len(payload), payload)


def main(path: str) -> int:
    with open(path, encoding="utf-8") as fh:
        records = signed_records(fh.read())
    if not records:
        print(f"no signed records found in {path}")
        return 1
    key = ec.derive_private_key(DEMO_SCALAR, ec.SECP256R1())
    algorithm = ec.ECDSA(hashes.SHA256(), deterministic_signing=True)
    ok = True
    for i, record in enumerate(records, start=1):
        cb = covered_bytes(record)
        fingerprint = hashlib.sha256(cb).hexdigest()
        signature = base64.b64encode(key.sign(dsse_pae(cb), algorithm)).decode()
        fp_ok = fingerprint == record["attestation_list"][0]["fingerprint"]["value"]
        sig_ok = signature == record["unmapped"]["signature_b64"]
        print(f"record {i}: fingerprint identical={fp_ok} signature identical={sig_ok}")
        ok = ok and fp_ok and sig_ok
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
