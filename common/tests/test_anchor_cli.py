"""End-to-end: Case File anchor artifacts verify via the shipped CLI (#408).

Exercises the real verifier (cli/ai_identity_verify.py) against the exact
JSON the bundle ships, using only the public key — the auditor's position.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.forensic import anchor_service
from common.forensic.signer import SignerHandle
from common.models.audit_log import AuditLog
from common.models.organization import Organization

_REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "ai_identity_verify", _REPO / "cli" / "ai_identity_verify.py"
)
verify_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_cli)


def _signer_and_pubkey(tmp_path):
    priv = ec.generate_private_key(ec.SECP256R1())
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path = tmp_path / "pubkey.pem"
    pub_path.write_bytes(pub_pem)
    handle = SignerHandle(
        sign=lambda m: priv.sign(m, ec.ECDSA(hashes.SHA256())),
        key_id="local:cli-test",
        backend="local",
    )
    return handle, str(pub_path)


def _seed(db, test_user, test_agent, n):
    org = Organization(name="CLI Org", owner_id=test_user.id)
    db.add(org)
    db.commit()
    db.refresh(org)
    ids = []
    for i in range(n):
        row = AuditLog(
            agent_id=test_agent.id,
            org_id=org.id,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
            entry_hash=hashlib.sha256(f"cli-{i}".encode()).hexdigest(),
            prev_hash="GENESIS" if i == 0 else "x" * 64,
        )
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    return org, ids


def _write_bundle(tmp_path, db, org, audit_ids):
    evidence = anchor_service.assemble_evidence(db, org.id, audit_ids)
    cp_path = tmp_path / "checkpoints.json"
    pf_path = tmp_path / "inclusion-proofs.json"
    cp_path.write_text(json.dumps(evidence["checkpoints"]))
    pf_path.write_text(json.dumps({"proofs": evidence["proofs"], "pending": evidence["pending"]}))
    return str(cp_path), str(pf_path)


def test_cli_verifies_inclusion_with_public_key(tmp_path, db_session, test_user, test_agent):
    org, ids = _seed(db_session, test_user, test_agent, 30)
    signer, pub_path = _signer_and_pubkey(tmp_path)
    anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    cp_path, pf_path = _write_bundle(tmp_path, db_session, org, ids)

    rc = verify_cli.main(
        [
            "--no-color",
            "inclusion-proof",
            "--checkpoints",
            cp_path,
            "--proofs",
            pf_path,
            "--pubkey",
            pub_path,
        ]
    )
    assert rc == 0


def test_cli_rejects_tampered_proof(tmp_path, db_session, test_user, test_agent):
    org, ids = _seed(db_session, test_user, test_agent, 30)
    signer, pub_path = _signer_and_pubkey(tmp_path)
    anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    cp_path, pf_path = _write_bundle(tmp_path, db_session, org, ids)

    doc = json.loads(pathlib.Path(pf_path).read_text())
    doc["proofs"][0]["entry_hash"] = hashlib.sha256(b"forged").hexdigest()
    pathlib.Path(pf_path).write_text(json.dumps(doc))

    rc = verify_cli.main(
        [
            "--no-color",
            "inclusion-proof",
            "--checkpoints",
            cp_path,
            "--proofs",
            pf_path,
            "--pubkey",
            pub_path,
        ]
    )
    assert rc == 1


def test_cli_rejects_wrong_public_key(tmp_path, db_session, test_user, test_agent):
    org, ids = _seed(db_session, test_user, test_agent, 12)
    signer, _ = _signer_and_pubkey(tmp_path)
    anchor_service.create_checkpoint(db_session, org.id, signer=signer)
    cp_path, pf_path = _write_bundle(tmp_path, db_session, org, ids)

    # A different key than the one that signed the checkpoint.
    _, other_pub = _signer_and_pubkey(tmp_path)
    rc = verify_cli.main(
        [
            "--no-color",
            "inclusion-proof",
            "--checkpoints",
            cp_path,
            "--proofs",
            pf_path,
            "--pubkey",
            other_pub,
        ]
    )
    assert rc == 1
