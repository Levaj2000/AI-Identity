"""Build a sample OCSF ``attestation_finding`` event (PR #1689 shape) from a
real Evidence Anchor checkpoint over real production gateway events.

Two variants of the SAME finding are emitted:

- ``attestation-finding.as-1689.json`` — strictly the #1689 schema at commit
  cffd386e: ``finding_info.related_events`` reference events by uid/type_uid
  only. No hash exists anywhere, so a verifier cannot recompute the Merkle
  root — membership integrity is unverifiable by construction.
- ``attestation-finding.with-hashes.json`` — identical except each reference
  additionally carries ``record_hash`` (the event's attestation hash). One
  added field; the root becomes recomputable and edits/substitutions of any
  referenced record are detectable offline.

Source events are drawn verbatim from the shared production reference bundle
(docs/cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle-2026-07-03.zip, 174
events, per-event signatures verified against the production JWKS). The
checkpoint is built and signed by the PRODUCTION code path
(common/forensic/merkle.py + anchor_checkpoint.py); the signing key is a
demo P-256 key generated here (production uses the KMS-backed signer), with
the public key written alongside so the artifact verifies offline.

Run:  .venv/bin/python docs/cosai-ws4-ocsf-mapping/attestation-finding-sample/build_sample.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
import uuid
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402

from common.forensic import anchor_checkpoint  # noqa: E402

HERE = Path(__file__).resolve().parent
BUNDLE_ZIP = REPO / "docs/cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle-2026-07-03.zip"
BATCH_SIZE = 8

OCSF_VERSION = "1.9.0-dev"
CLASS_UID = 2009  # attestation_finding: findings category (2), Dave's uid 9
TYPE_UID = CLASS_UID * 100 + 1  # activity 1 = Create


def load_batch() -> list[dict]:
    with zipfile.ZipFile(BUNDLE_ZIP) as zf:
        lines = zf.read("production-ocsf-full-export.ocsf.ndjson").decode().splitlines()
    events = [json.loads(ln) for ln in lines if ln.strip()]
    chained = [e for e in events if e.get("attestation", {}).get("entry_hash")]
    chained.sort(key=lambda e: int(e["attestation"]["uid"]))
    return chained[-BATCH_SIZE:]


def build() -> None:
    batch = load_batch()
    org_id = uuid.UUID(batch[0]["attestation"]["chain_uid"])
    entry_hashes = [e["attestation"]["entry_hash"]["value"] for e in batch]
    first_id = int(batch[0]["attestation"]["uid"])
    last_id = int(batch[-1]["attestation"]["uid"])

    # Demo signing key (production signs with the KMS-backed forensic signer;
    # the construction, canonicalization, and verification are identical).
    private_key = ec.generate_private_key(ec.SECP256R1())
    spki = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    key_id = "local:" + hashlib.sha256(spki).hexdigest()
    signed_at = datetime.datetime.now(datetime.UTC)

    checkpoint, tree = anchor_checkpoint.build_checkpoint(
        org_id=org_id,
        entry_hashes=entry_hashes,
        first_audit_id=first_id,
        last_audit_id=last_id,
        signer_key_id=key_id,
        signed_at=signed_at,
    )
    envelope = anchor_checkpoint.sign_checkpoint(
        checkpoint, lambda b: private_key.sign(b, ec.ECDSA(hashes.SHA256()))
    )
    # Round-trip through the production verifier before emitting anything.
    pub_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    anchor_checkpoint.verify_checkpoint(envelope, pub_pem)

    signed_at_ms = int(signed_at.timestamp() * 1000)
    root_hex = tree.root.hex()
    authority_uid = f"ai-identity:evidence-anchor:org/{org_id}"

    proofs = {
        "leaf_rule": "leaf_data = bytes.fromhex(attestation.entry_hash.value); RFC 6962 domain separation",
        "tree_size": tree.size,
        "merkle_root": root_hex,
        "proofs": [
            {
                "ref_index": i,
                "event_uid": e["attestation"]["uid"],
                "entry_hash": entry_hashes[i],
                "audit_path": [p.hex() for p in tree.inclusion_proof(i)],
            }
            for i, e in enumerate(batch)
        ],
    }

    def finding(with_hashes: bool) -> dict:
        refs = []
        for e in batch:
            ref: dict = {"uid": e["attestation"]["uid"], "type_uid": e["type_uid"]}
            if with_hashes:
                # THE one added field: content-binding hash on each reference.
                ref["record_hash"] = dict(e["attestation"]["entry_hash"])
            refs.append(ref)
        return {
            "activity_id": 1,
            "activity_name": "Create",
            "category_uid": 2,
            "class_uid": CLASS_UID,
            "type_uid": TYPE_UID,
            "severity_id": 1,
            "time": signed_at_ms,
            "metadata": {
                "version": OCSF_VERSION,
                "profiles": ["record_integrity"],
                "uid": f"anchor-checkpoint:{org_id}:{first_id}-{last_id}",
                "product": {
                    "name": "AI Identity Gateway — Evidence Anchor",
                    "vendor_name": "AI Identity",
                },
            },
            "attestation_authority_uid": authority_uid,
            "finding_info": {
                "uid": f"anchor-checkpoint:{org_id}:{first_id}-{last_id}",
                "title": f"Evidence Anchor checkpoint over {tree.size} gateway audit events",
                "desc": (
                    "Signed RFC 6962 Merkle checkpoint committing to the ordered set of "
                    "referenced events. The signature's digest is the Merkle root over the "
                    "referenced records' attestation hashes."
                ),
                "created_time": signed_at_ms,
                "related_events": refs,
            },
            "attestation_list": [
                {
                    "attestation_authority_uid": authority_uid,
                    "signatures": [
                        {
                            "algorithm_id": 3,
                            "algorithm": "ECDSA-P256-SHA256",
                            "created_time": signed_at_ms,
                            "digest": {
                                "algorithm_id": 3,
                                "algorithm": "SHA-256",
                                "value": root_hex,
                            },
                        }
                    ],
                }
            ],
            "unmapped": {
                # Signature bytes / key id / envelope have no OCSF home (same
                # convention as the reference bundle's per-event signatures).
                "evidence_anchor": {
                    "checkpoint": checkpoint.to_canonical_dict(),
                    "dsse_envelope": envelope.model_dump(),
                }
            },
        }

    (HERE / "source-events.ocsf.ndjson").write_text(
        "\n".join(json.dumps(e, separators=(",", ":")) for e in batch) + "\n"
    )
    (HERE / "attestation-finding.as-1689.json").write_text(
        json.dumps(finding(False), indent=2) + "\n"
    )
    (HERE / "attestation-finding.with-hashes.json").write_text(
        json.dumps(finding(True), indent=2) + "\n"
    )
    (HERE / "evidence-anchor-checkpoint.dsse.json").write_text(
        json.dumps(envelope.model_dump(), indent=2) + "\n"
    )
    (HERE / "inclusion-proofs.json").write_text(json.dumps(proofs, indent=2) + "\n")
    (HERE / "checkpoint-public-key.pem").write_bytes(pub_pem)

    print(f"batch: audit ids {first_id}..{last_id} ({tree.size} events), org {org_id}")
    print(f"merkle_root: {root_hex}")
    print("checkpoint verified round-trip via production verifier: OK")
    print(f"wrote 6 artifacts to {HERE}")


if __name__ == "__main__":
    build()
