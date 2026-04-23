"""Unit tests for the ZIP writer + DSSE manifest signer.

Exercises the bundle/manifest plumbing without a database so failures
point at the code under test rather than ORM glue.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import uuid
import zipfile

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from common.compliance.bundle import BundleAlreadySealedError, ComplianceExportBundle
from common.compliance.manifest import (
    EXPORT_MANIFEST_PAYLOAD_TYPE,
    MANIFEST_SCHEMA_VERSION,
    build_manifest,
    sign_manifest,
)
from common.forensic.signer import SignerHandle
from common.schemas.forensic_attestation import pae


def _local_signer() -> tuple[SignerHandle, bytes]:
    """In-process ECDSA-P256 signer with a fresh keypair per call."""
    pk = ec.generate_private_key(ec.SECP256R1())

    def sign(message: bytes) -> bytes:
        return pk.sign(message, ec.ECDSA(hashes.SHA256()))

    public_pem = pk.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return (
        SignerHandle(sign=sign, key_id="local:test", backend="local"),
        public_pem,
    )


def _now() -> datetime.datetime:
    return datetime.datetime(2026, 4, 23, 12, 0, tzinfo=datetime.UTC)


# ── Manifest builder ─────────────────────────────────────────────────


class TestBuildManifest:
    def test_shape_includes_required_fields(self):
        manifest = build_manifest(
            export_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            org_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            profile="soc2_tsc_2017",
            audit_period_start=_now(),
            audit_period_end=_now() + datetime.timedelta(days=30),
            built_at=_now() + datetime.timedelta(days=30, minutes=1),
            signer_key_id="local:test",
            artifacts=[{"path": "x", "sha256": "y" * 64, "bytes": 1, "controls": []}],
        )
        assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
        assert manifest["profile"] == "soc2_tsc_2017"
        assert manifest["signer_key_id"] == "local:test"
        assert manifest["audit_period_start"].endswith("Z")
        assert len(manifest["artifacts"]) == 1

    def test_naive_timestamp_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            build_manifest(
                export_id=uuid.uuid4(),
                org_id=uuid.uuid4(),
                profile="soc2_tsc_2017",
                audit_period_start=datetime.datetime(2026, 1, 1),  # naive
                audit_period_end=_now(),
                built_at=_now(),
                signer_key_id="x",
                artifacts=[],
            )


# ── Sign manifest ────────────────────────────────────────────────────


class TestSignManifest:
    def test_envelope_payload_type_is_domain_separated(self):
        signer, _ = _local_signer()
        manifest = build_manifest(
            export_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            profile="soc2_tsc_2017",
            audit_period_start=_now(),
            audit_period_end=_now() + datetime.timedelta(days=1),
            built_at=_now(),
            signer_key_id=signer.key_id,
            artifacts=[],
        )
        env = sign_manifest(manifest, signer)
        assert env.payloadType == EXPORT_MANIFEST_PAYLOAD_TYPE
        # Must NOT match the attestation payloadType.
        assert "attestation" not in env.payloadType

    def test_envelope_verifies_against_public_key(self):
        signer, public_pem = _local_signer()
        manifest = build_manifest(
            export_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            profile="soc2_tsc_2017",
            audit_period_start=_now(),
            audit_period_end=_now() + datetime.timedelta(days=1),
            built_at=_now(),
            signer_key_id=signer.key_id,
            artifacts=[],
        )
        env = sign_manifest(manifest, signer)
        payload = base64.b64decode(env.payload)
        signing_input = pae(env.payloadType, payload)
        sig = base64.b64decode(env.signatures[0].sig)
        pk = serialization.load_pem_public_key(public_pem)
        pk.verify(sig, signing_input, ec.ECDSA(hashes.SHA256()))  # raises on failure

    def test_tampered_payload_fails_verification(self):
        signer, public_pem = _local_signer()
        manifest = build_manifest(
            export_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            profile="soc2_tsc_2017",
            audit_period_start=_now(),
            audit_period_end=_now() + datetime.timedelta(days=1),
            built_at=_now(),
            signer_key_id=signer.key_id,
            artifacts=[],
        )
        env = sign_manifest(manifest, signer)
        tampered_payload = base64.b64decode(env.payload).replace(
            b"soc2_tsc_2017", b"eu_ai_act_2024"
        )
        signing_input = pae(env.payloadType, tampered_payload)
        sig = base64.b64decode(env.signatures[0].sig)
        pk = serialization.load_pem_public_key(public_pem)
        from cryptography.exceptions import InvalidSignature

        with pytest.raises(InvalidSignature):
            pk.verify(sig, signing_input, ec.ECDSA(hashes.SHA256()))


# ── Bundle writer ────────────────────────────────────────────────────


class TestBundle:
    def test_roundtrip_writes_and_hashes_match(self, tmp_path):
        signer, _ = _local_signer()
        export_id = uuid.uuid4()
        bundle = ComplianceExportBundle.create(tmp_path / "export.zip", export_id=export_id)
        bundle.write_text("README.md", "hello world")
        bundle.write_text("PLACEHOLDER.txt", "placeholder")
        bundle.seal(
            profile="soc2_tsc_2017",
            audit_period_start=_now(),
            audit_period_end=_now() + datetime.timedelta(days=1),
            built_at=_now(),
            org_id=uuid.uuid4(),
            signer=signer,
        )
        # Archive hash matches on-disk bytes.
        on_disk = (tmp_path / "export.zip").read_bytes()
        assert bundle.archive_sha256 == hashlib.sha256(on_disk).hexdigest()
        assert bundle.archive_bytes == len(on_disk)

        # Archive contains both artifacts + manifest files.
        with zipfile.ZipFile(tmp_path / "export.zip") as zf:
            names = set(zf.namelist())
            assert {"README.md", "PLACEHOLDER.txt", "manifest.json", "manifest.dsse.json"} <= names
            readme_hash = hashlib.sha256(zf.read("README.md")).hexdigest()

        # Manifest commits to the actual file hashes.
        env = bundle.manifest_envelope
        manifest = json.loads(base64.b64decode(env.payload))
        readme_entry = next(a for a in manifest["artifacts"] if a["path"] == "README.md")
        assert readme_entry["sha256"] == readme_hash

    def test_seal_then_write_raises(self, tmp_path):
        signer, _ = _local_signer()
        bundle = ComplianceExportBundle.create(tmp_path / "x.zip", export_id=uuid.uuid4())
        bundle.write_text("A.txt", "a")
        bundle.seal(
            profile="soc2_tsc_2017",
            audit_period_start=_now(),
            audit_period_end=_now() + datetime.timedelta(days=1),
            built_at=_now(),
            org_id=uuid.uuid4(),
            signer=signer,
        )
        with pytest.raises(BundleAlreadySealedError):
            bundle.write_text("B.txt", "b")

    def test_duplicate_path_rejected(self, tmp_path):
        signer, _ = _local_signer()
        bundle = ComplianceExportBundle.create(tmp_path / "x.zip", export_id=uuid.uuid4())
        bundle.write_text("A.txt", "first")
        with pytest.raises(ValueError, match="duplicate bundle path"):
            bundle.write_text("A.txt", "second")

    def test_existing_archive_path_rejected(self, tmp_path):
        path = tmp_path / "x.zip"
        path.write_bytes(b"not a zip")
        with pytest.raises(FileExistsError):
            ComplianceExportBundle.create(path, export_id=uuid.uuid4())
