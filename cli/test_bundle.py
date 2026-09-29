#!/usr/bin/env python3
"""Tests for the `bundle` subcommand (Case File bundle format v1).

Each test builds a real bundle: a per-org chain, a checkpoint signed with an
in-memory P-256 key, RFC 6962 inclusion proofs computed independently of the
CLI, optional retention tombstones, and a DSSE-signed manifest.json. The
spec under test is docs/forensics/export-bundle-format.md.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from typing import Any
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

import ai_identity_verify as cli
from test_verify import (
    _TOMB_ORG_ID,
    TEST_HMAC_KEY,
    _audit_path,
    _build_org_chain,
    _have_cryptography,
    _local_ecdsa_signer,
    _make_entry_hash,
    _make_report_signature,
    _pae,
    _pruned_export,
    _run_cmd,
)

KID = "local:test"  # the keyid _checkpoint_envelope signs under
REPORT = "case-file-f1e2d3c4-2026-09-29.json"
CHECKPOINTS = "evidence-anchor/checkpoints.json"
PROOFS = "evidence-anchor/inclusion-proofs.json"
TOMBSTONES = "retention/tombstones.json"
MANIFEST_TYPE = "application/vnd.ai-identity.case-file-manifest+json"
ROLES = {
    REPORT: "report",
    "ai_identity_verify.py": "verifier",
    "verify.command": "runner",
    "README.md": "readme",
    CHECKPOINTS: "checkpoints",
    PROOFS: "proofs",
    TOMBSTONES: "tombstones",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(_have_cryptography(), "cryptography package not installed")
class TestBundleVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cryptography.hazmat.primitives.asymmetric import ec

        cls.private_key = ec.generate_private_key(ec.SECP256R1())
        cls.signer = staticmethod(_local_ecdsa_signer(cls.private_key))
        cls.tmp = tempfile.mkdtemp()
        nums = cls.private_key.public_key().public_numbers()
        cls.jwks_path = os.path.join(cls.tmp, "jwks.json")
        with open(cls.jwks_path, "w", encoding="utf-8") as f:
            json.dump({"keys": [cls._jwk(nums, KID)]}, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @staticmethod
    def _jwk(nums: Any, kid: str) -> dict[str, Any]:
        def b64(n: int) -> str:
            return base64.urlsafe_b64encode(n.to_bytes(32, "big")).rstrip(b"=").decode()

        return {"kty": "EC", "crv": "P-256", "x": b64(nums.x), "y": b64(nums.y), "kid": kid}

    # -- Bundle factory ---------------------------------------------------

    def _parts(
        self,
        count: int = 6,
        prune: tuple[int, ...] = (),
        pending: tuple[int, ...] = (),
        scope_type: str = "org",
    ) -> dict[str, Any]:
        """Every artifact of a bundle, as Python objects (JSON) or bytes."""
        report, tomb_doc = _pruned_export(count=count, prune=prune, signer=self.signer)
        leaves = [e["entry_hash"] for e in _build_org_chain(count)]
        root = tomb_doc["checkpoints"][0]["merkle_root"]
        proofs = [
            {
                "audit_id": e["id"],
                "entry_hash": e["entry_hash"],
                "index": e["id"] - 1,
                "tree_size": count,
                "merkle_root": root,
                "proof": _audit_path(e["id"] - 1, leaves),
            }
            for e in report["events"]
            if e["id"] not in pending
        ]
        report["scope"] = {"type": scope_type, "org_id": _TOMB_ORG_ID}
        parts: dict[str, Any] = {
            REPORT: report,
            CHECKPOINTS: [
                {"merkle_root": root, "envelope": tomb_doc["checkpoints"][0]["envelope"]}
            ],
            PROOFS: {"proofs": proofs, "pending": list(pending)},
            "ai_identity_verify.py": b"# embedded verifier\n",
            "verify.command": b"#!/bin/sh\n",
            "README.md": b"# Case File\n",
        }
        if prune:
            parts[TOMBSTONES] = tomb_doc
        return parts

    def _manifest_payload(self, files: dict[str, bytes], parts: dict[str, Any]) -> dict[str, Any]:
        ids = [e["id"] for e in parts[REPORT]["events"]]
        proofs_doc = parts.get(PROOFS)
        return {
            "schema_version": 1,
            "format": "ai-identity-case-file/v1",
            "bundle_id": "b-0001",
            "generated_at": "2026-09-29T15:04:11Z",
            "generator": "test-builder",
            "signer_key_id": KID,
            "org_id": _TOMB_ORG_ID,
            "scope": parts[REPORT]["scope"],
            "range": {"first_audit_id": min(ids), "last_audit_id": max(ids)} if ids else None,
            "counts": {
                "events": len(ids),
                "anchored": len(proofs_doc["proofs"]) if proofs_doc else 0,
                "pending": len(proofs_doc["pending"]) if proofs_doc else len(ids),
                "tombstoned": len(parts[TOMBSTONES]["tombstones"]) if TOMBSTONES in parts else 0,
            },
            "verifier_version": cli.__version__,
            "files": [
                {"path": p, "sha256": _sha256(b), "role": ROLES[p]}
                for p, b in sorted(files.items())
            ],
        }

    def _envelope(self, payload_type: str, payload: dict[str, Any], signer=None) -> bytes:
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        sig = (signer or self.signer)(_pae(payload_type, payload_bytes))
        envelope = {
            "payloadType": payload_type,
            "payload": base64.b64encode(payload_bytes).decode("ascii"),
            "signatures": [{"keyid": KID, "sig": base64.b64encode(sig).decode("ascii")}],
        }
        return json.dumps(envelope).encode()

    def _files(self, parts: dict[str, Any], manifest: bool = True, edit=None) -> dict[str, bytes]:
        """Serialize parts; sign a manifest over them unless manifest=False.

        ``edit`` receives the manifest payload before signing, so a test can
        make the issuer's own statement wrong while keeping it validly signed.
        """
        files = {p: v if isinstance(v, bytes) else json.dumps(v).encode() for p, v in parts.items()}
        if manifest:
            payload = self._manifest_payload(files, parts)
            if edit is not None:
                edit(payload)
            files["manifest.json"] = self._envelope(MANIFEST_TYPE, payload)
        return files

    def _zip(self, files: dict[str, bytes], names: list[str] | None = None) -> str:
        fd, path = tempfile.mkstemp(suffix=".zip", dir=self.tmp)
        os.close(fd)
        with zipfile.ZipFile(path, "w") as zf:
            for name in names or sorted(files):
                zf.writestr(name, files[name])
        return path

    def _run(self, target: str, *extra: str, key: str = TEST_HMAC_KEY):
        code, out, err = _run_cmd(
            ["--json", "bundle", target, "--jwks", self.jwks_path, *extra], env_key=key
        )
        return code, (json.loads(out) if out.strip().startswith("{") else None), err

    def _assert_rejected(self, files: dict[str, bytes], tier: str, needle: str, key=TEST_HMAC_KEY):
        code, result, err = self._run(self._zip(files), key=key)
        self.assertEqual(code, 1, err)
        self.assertEqual(result["result"], "rejected")
        self.assertEqual(result["tiers"][tier]["outcome"], "REJECTED", result["tiers"])
        self.assertIn(needle, result["tiers"][tier]["reason"])
        return result

    # -- A valid bundle ---------------------------------------------------

    def test_valid_bundle_verifies_every_tier_it_can(self):
        code, result, err = self._run(self._zip(self._files(self._parts())))
        self.assertEqual(code, 0, err)
        self.assertEqual(result["result"], "verified")
        self.assertEqual(result["format"], "ai-identity-case-file/v1")
        p, k, w = (result["tiers"][t] for t in ("P", "K", "W"))
        self.assertEqual(p["outcome"], "VERIFIED")
        self.assertEqual((p["anchored"], p["pending"], p["tombstoned"]), (6, 0, 0))
        self.assertTrue(p["completeness_claimed"])
        self.assertEqual(k["outcome"], "VERIFIED")
        self.assertEqual((k["entries_verified"], k["entries_not_covered"]), (6, 0))
        self.assertEqual(w["outcome"], "UNAVAILABLE")

    def test_human_output_reports_tiers_separately_in_ascii(self):
        path = self._zip(self._files(self._parts()))
        code, out, _ = _run_cmd(["--no-color", "bundle", path, "--jwks", self.jwks_path])
        self.assertEqual(code, 0)
        self.assertIn("manifest signature valid", out)
        self.assertIn("Tier P:   VERIFIED     6 anchored, 0 pending, 0 tombstoned", out)
        self.assertIn("Tier K:   VERIFIED     6/6 rows under supplied keys", out)
        self.assertIn("Tier W:   UNAVAILABLE", out)
        self.assertTrue(out.isascii())

    def test_extracted_directory_verifies_and_ignores_ds_store(self):
        files = self._files(self._parts())
        root = tempfile.mkdtemp(dir=self.tmp)
        for name, data in files.items():
            os.makedirs(os.path.dirname(os.path.join(root, name)), exist_ok=True)
            with open(os.path.join(root, name), "wb") as f:
                f.write(data)
        with open(os.path.join(root, ".DS_Store"), "wb") as f:
            f.write(b"\x00")
        code, result, err = self._run(root)
        self.assertEqual(code, 0, err)
        self.assertEqual(result["tiers"]["P"]["outcome"], "VERIFIED")

    def test_pending_events_and_tombstoned_gap_verify(self):
        parts = self._parts(count=8, prune=(3, 4), pending=(8,))
        code, result, err = self._run(self._zip(self._files(parts)))
        self.assertEqual(code, 0, err)
        p = result["tiers"]["P"]
        self.assertEqual((p["anchored"], p["pending"], p["tombstoned"]), (5, 1, 2))

    def test_stranger_without_key_gets_tier_p_and_tier_k_unavailable(self):
        code, result, _ = self._run(self._zip(self._files(self._parts())), key="")
        self.assertEqual(code, 0)
        self.assertEqual(result["tiers"]["P"]["outcome"], "VERIFIED")
        self.assertEqual(result["tiers"]["K"]["outcome"], "UNAVAILABLE")
        self.assertIn("no key supplied", result["tiers"]["K"]["reason"])

    def test_pinned_pubkey_verifies(self):
        from cryptography.hazmat.primitives import serialization

        pem = os.path.join(self.tmp, "signer.pem")
        with open(pem, "wb") as f:
            f.write(
                self.private_key.public_key().public_bytes(
                    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )
        path = self._zip(self._files(self._parts()))
        code, out, err = _run_cmd(["--json", "bundle", path, "--pubkey", pem])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["result"], "verified")

    # -- What the signed manifest buys a stranger -------------------------

    def test_edited_row_is_caught_at_tier_p_without_any_key(self):
        """The spec's headline case: content edited after issuance, entry_hash
        label left alone. Inclusion proofs alone cannot see this."""
        files = self._files(self._parts())
        report = json.loads(files[REPORT])
        report["events"][2]["decision"] = "deny"
        files[REPORT] = json.dumps(report).encode()
        result = self._assert_rejected(files, "P", "SHA-256 does not match", key="")
        self.assertEqual(result["tiers"]["P"]["artifact"], REPORT)

    def test_reforged_org_chain_is_caught_at_tier_p(self):
        """An org admin holds the org key and re-forges the chain; Tier K would
        pass, but the platform-signed manifest does not."""
        parts = self._parts()
        files = self._files(parts)
        report = json.loads(files[REPORT])
        prev = report["events"][0]["prev_hash_org"]
        for i, e in enumerate(report["events"]):
            if i == 2:
                e["decision"] = "deny"
            e["prev_hash_org"] = prev
            e["entry_hash_org"] = _make_entry_hash(
                agent_id=e["agent_id"],
                endpoint=e["endpoint"],
                method=e["method"],
                decision=e["decision"],
                cost_estimate_usd=e["cost_estimate_usd"],
                latency_ms=e["latency_ms"],
                request_metadata=e["request_metadata"],
                created_at=e["created_at"],
                prev_hash=prev,
            )
            prev = e["entry_hash_org"]
        report["report_signature"] = _make_report_signature(total_entries=6, entries_verified=6)
        files[REPORT] = json.dumps(report).encode()
        self._assert_rejected(files, "P", "SHA-256 does not match")

    def test_manifest_signed_by_another_key_rejected(self):
        from cryptography.hazmat.primitives.asymmetric import ec

        other = _local_ecdsa_signer(ec.generate_private_key(ec.SECP256R1()))
        parts = self._parts()
        files = self._files(parts, manifest=False)
        files["manifest.json"] = self._envelope(
            MANIFEST_TYPE, self._manifest_payload(files, parts), signer=other
        )
        self._assert_rejected(files, "P", "signature does not verify")

    def test_file_outside_inventory_rejected(self):
        files = self._files(self._parts())
        files["notes.txt"] = b"added after issuance"
        self._assert_rejected(files, "P", "notes.txt is not in the signed manifest inventory")

    def test_stripping_retention_folder_is_rejected_not_downgraded(self):
        files = self._files(self._parts(count=8, prune=(3,)))
        del files[TOMBSTONES]
        self._assert_rejected(files, "P", "listed in the manifest but missing")

    def test_stripping_manifest_reads_as_pre_v1_never_verified(self):
        files = self._files(self._parts())
        del files["manifest.json"]
        code, result, _ = self._run(self._zip(files))
        self.assertEqual(code, cli.EXIT_NOT_VERIFIED)
        self.assertEqual(result["result"], "pre_v1")
        self.assertEqual(result["tiers"]["P"]["outcome"], "PRE-V1")
        self.assertEqual(result["tiers"]["K"]["outcome"], "VERIFIED")

    def test_unknown_format_and_schema_version_rejected(self):
        parts = self._parts()
        files = self._files(parts, edit=lambda m: m.update(format="ai-identity-case-file/v2"))
        self._assert_rejected(files, "P", "this verifier understands 'ai-identity-case-file/v1'")
        files = self._files(parts, edit=lambda m: m.update(schema_version=2))
        self._assert_rejected(files, "P", "schema_version 2")

    def test_manifest_scope_or_counts_disagreeing_with_report_rejected(self):
        parts = self._parts()
        files = self._files(parts, edit=lambda m: m["scope"].update(type="agent"))
        self._assert_rejected(files, "P", "scope does not match")
        files = self._files(parts, edit=lambda m: m["counts"].update(events=5))
        self._assert_rejected(files, "P", "6 events, the signed manifest says 5")
        files = self._files(parts, edit=lambda m: m["counts"].update(pending=1))
        self._assert_rejected(files, "P", "counts do not match the proofs file")

    # -- Anchor checks ----------------------------------------------------

    def test_row_hash_differing_from_anchored_leaf_rejected(self):
        parts = self._parts()
        parts[REPORT]["events"][1]["entry_hash"] = "ab" * 32
        self._assert_rejected(self._files(parts), "P", "entry_hash is not the anchored one")

    def test_event_missing_from_proofs_and_pending_rejected(self):
        parts = self._parts(pending=(6,))
        parts[PROOFS]["pending"] = []
        files = self._files(parts, edit=lambda m: m["counts"].update(pending=1))
        self._assert_rejected(files, "P", "unaccounted events [6]")

    def test_proof_tree_size_must_match_signed_checkpoint(self):
        parts = self._parts()
        parts[PROOFS]["proofs"][0]["tree_size"] = 7
        self._assert_rejected(self._files(parts), "P", "tree_size differs from the signed one")

    def test_broken_audit_path_rejected(self):
        parts = self._parts()
        parts[PROOFS]["proofs"][0]["proof"][0] = "00" * 32
        self._assert_rejected(self._files(parts), "P", "audit path does not reach the signed root")

    def test_checkpoint_with_unknown_schema_version_rejected(self):
        parts = self._parts()
        entry = parts[CHECKPOINTS][0]
        payload = json.loads(base64.b64decode(entry["envelope"]["payload"]))
        payload["schema_version"] = 2
        entry["envelope"] = json.loads(
            self._envelope(cli.CHECKPOINT_PAYLOAD_TYPE, payload).decode()
        )
        self._assert_rejected(self._files(parts), "P", "schema_version 2")

    def test_checkpoint_for_another_org_rejected(self):
        parts = self._parts()
        entry = parts[CHECKPOINTS][0]
        payload = json.loads(base64.b64decode(entry["envelope"]["payload"]))
        payload["org_id"] = "00000000-0000-4000-8000-000000000000"
        entry["envelope"] = json.loads(
            self._envelope(cli.CHECKPOINT_PAYLOAD_TYPE, payload).decode()
        )
        self._assert_rejected(self._files(parts), "P", "is for org")

    # -- Structure and retention ------------------------------------------

    def test_gap_without_tombstones_is_unaccounted_deletion(self):
        parts = self._parts(count=8, prune=(3,))
        del parts[TOMBSTONES]
        self._assert_rejected(self._files(parts), "P", "unaccounted deletion")

    def test_tombstone_with_wrong_leaf_rejected(self):
        parts = self._parts(count=8, prune=(3,))
        parts[TOMBSTONES]["tombstones"][0]["entry_hash"] = "cd" * 32
        self._assert_rejected(self._files(parts), "P", "entry_hash is not the signed leaf")

    def test_tombstone_receipt_must_be_present(self):
        parts = self._parts(count=8, prune=(3,))
        parts[TOMBSTONES]["receipts"] = []
        self._assert_rejected(self._files(parts), "P", "receipt missing or not chained")

    def test_incident_scope_is_a_slice_without_completeness_claim(self):
        parts = self._parts(count=8, prune=(3, 4), scope_type="incident")
        del parts[TOMBSTONES]
        code, result, err = self._run(self._zip(self._files(parts)))
        self.assertEqual(code, 0, err)
        self.assertEqual(result["tiers"]["P"]["outcome"], "VERIFIED")
        self.assertFalse(result["tiers"]["P"]["completeness_claimed"])

    def test_unknown_scope_type_rejected(self):
        parts = self._parts(scope_type="tenant")
        self._assert_rejected(self._files(parts), "P", "unknown scope type 'tenant'")

    # -- Tier K -----------------------------------------------------------

    def test_tier_k_catches_edited_row_in_pre_v1_bundle(self):
        parts = self._parts()
        parts[REPORT]["events"][3]["decision"] = "deny"
        files = self._files(parts, manifest=False)
        result = self._assert_rejected(files, "K", "entry_hash_org does not match its content")
        self.assertEqual(result["tiers"]["P"]["outcome"], "PRE-V1")

    def test_key_from_another_epoch_is_unavailable_not_rejected(self):
        parts = self._parts()
        for e in parts[REPORT]["events"]:
            e["key_fingerprint"] = cli._key_fingerprint(TEST_HMAC_KEY.encode())
        code, result, _ = self._run(self._zip(self._files(parts)), key="some-other-key")
        self.assertEqual(code, 0)
        self.assertEqual(result["tiers"]["K"]["outcome"], "UNAVAILABLE")
        self.assertIn("no key coverage", result["tiers"]["K"]["reason"])

    def test_platform_claiming_invalid_chain_rejected(self):
        parts = self._parts()
        report = parts[REPORT]
        report["chain_verification"]["chain_valid"] = False
        report["report_signature"] = _make_report_signature(
            chain_valid=False, total_entries=6, entries_verified=6
        )
        self._assert_rejected(self._files(parts), "K", "reports invalid")

    # -- Container and usage ----------------------------------------------

    def test_path_traversal_entry_rejected_before_anything_is_read(self):
        files = self._files(self._parts())
        files["../escape.txt"] = b"x"
        path = self._zip(files, names=sorted(files))
        code, result, _ = self._run(path)
        self.assertEqual(code, 1)
        self.assertEqual(result["tiers"]["P"]["artifact"], "container")
        self.assertIn("unsafe entry path", result["tiers"]["P"]["reason"])

    def test_key_source_is_required(self):
        path = self._zip(self._files(self._parts()))
        code, _, err = _run_cmd(["bundle", path])
        self.assertEqual(code, 2)
        self.assertIn("--jwks", err)

    def test_missing_bundle_is_a_usage_error(self):
        code, _, err = _run_cmd(["bundle", "/nonexistent/bundle.zip", "--jwks", self.jwks_path])
        self.assertEqual(code, 2)
        self.assertIn("Bundle not found", err)


class TestBundleWithoutCryptography(unittest.TestCase):
    """`bundle` needs ECDSA; a stdlib-only install gets the install hint, not a traceback."""

    def test_exits_cleanly_without_cryptography(self):
        blocked = {
            name: None
            for name in list(sys.modules)
            if name == "cryptography" or name.startswith("cryptography.")
        }
        blocked["cryptography"] = None
        with patch.dict(sys.modules, blocked):
            code, out, err = _run_cmd(["bundle", "whatever.zip", "--jwks", "jwks.json"])
        self.assertEqual(code, 2)
        self.assertIn("`bundle` command requires the `cryptography` package", err)
        self.assertNotIn("Traceback", out + err)


if __name__ == "__main__":
    unittest.main()
