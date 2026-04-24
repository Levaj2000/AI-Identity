"""ZIP bundle writer for compliance exports.

Streams files into a ZIP while accumulating per-file SHA-256 so the
manifest commits to the exact bytes inside the archive. The manifest
itself (DSSE envelope) is added last, after every artifact's hash is
known.

Typical flow:

    bundle = ComplianceExportBundle.create(tmp_path, export_id=...)
    bundle.write_text("README.md", "...")
    bundle.write_text("PLACEHOLDER.txt", "...")
    bundle.seal(
        profile="soc2_tsc_2017",
        audit_period_start=...,
        audit_period_end=...,
        org_id=...,
        signer=signer_handle,
    )
    # bundle.archive_path, bundle.archive_sha256, bundle.archive_bytes,
    # bundle.manifest_envelope are populated.

Sealed bundles are immutable — attempting to write after ``seal()``
raises ``BundleAlreadySealedError`` to prevent accidentally producing
a signed manifest that doesn't cover a later artifact.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from common.compliance.manifest import build_manifest, sign_manifest

if TYPE_CHECKING:
    import datetime
    import uuid
    from pathlib import Path

    from common.forensic.signer import SignerHandle
    from common.schemas.forensic_attestation import DSSEEnvelope


class BundleAlreadySealedError(RuntimeError):
    """Raised if a caller tries to mutate a bundle after ``seal()``."""


@dataclass
class _BundleEntry:
    path: str
    sha256: str
    size_bytes: int
    controls: list[str] = field(default_factory=list)


@dataclass
class ComplianceExportBundle:
    """A compliance-export ZIP under construction.

    Use :meth:`create` rather than the constructor so the archive file
    is opened in a consistent, append-friendly way.
    """

    export_id: uuid.UUID
    archive_path: Path
    _zip: zipfile.ZipFile
    _entries: list[_BundleEntry] = field(default_factory=list)
    _sealed: bool = False

    # Per-artifact schema versions surfaced into manifest.json so an
    # auditor can version-gate ingestion without parsing the CSV header.
    # Populated by profile builders (e.g. change_log.csv → "2.0").
    artifact_schema_versions: dict[str, str] = field(default_factory=dict)

    # Populated on seal() — None beforehand.
    archive_sha256: str | None = None
    archive_bytes: int | None = None
    manifest_envelope: DSSEEnvelope | None = None

    # ── Construction ───────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        archive_path: Path,
        *,
        export_id: uuid.UUID,
    ) -> ComplianceExportBundle:
        """Start a new bundle at ``archive_path``.

        ``archive_path`` must not exist — the caller owns the temp-dir
        / GCS-path decision. The file is opened in deflate mode for a
        reasonable size/time tradeoff on mostly-JSON/CSV payloads.
        """
        if archive_path.exists():
            msg = f"bundle path already exists: {archive_path}"
            raise FileExistsError(msg)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        zf = zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED)
        return cls(export_id=export_id, archive_path=archive_path, _zip=zf)

    # ── Write path ──────────────────────────────────────────────────

    def write_text(
        self,
        path: str,
        content: str,
        *,
        controls: list[str] | None = None,
    ) -> None:
        """Write a UTF-8 text artifact to ``path`` inside the archive."""
        self._assert_writable()
        self.write_bytes(path, content.encode("utf-8"), controls=controls)

    def write_bytes(
        self,
        path: str,
        content: bytes,
        *,
        controls: list[str] | None = None,
    ) -> None:
        """Write a binary artifact, accumulating its SHA-256 + size."""
        self._assert_writable()
        if any(e.path == path for e in self._entries):
            msg = f"duplicate bundle path: {path}"
            raise ValueError(msg)
        self._zip.writestr(path, content)
        self._entries.append(
            _BundleEntry(
                path=path,
                sha256=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                controls=list(controls or []),
            )
        )

    def write_json(
        self,
        path: str,
        obj: dict | list,
        *,
        controls: list[str] | None = None,
    ) -> None:
        """Write a pretty-printed JSON artifact.

        Readability matters for auditor-facing files — the manifest
        itself (and the one signed bytes) uses JCS separately. Here we
        optimize for the human who opens the archive in a text editor.
        """
        payload = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
        self.write_bytes(path, payload, controls=controls)

    # ── Seal + sign ─────────────────────────────────────────────────

    def seal(
        self,
        *,
        profile: str,
        audit_period_start: datetime.datetime,
        audit_period_end: datetime.datetime,
        built_at: datetime.datetime,
        org_id: uuid.UUID,
        signer: SignerHandle,
    ) -> None:
        """Write manifest.dsse.json into the archive and close it.

        After this call the bundle is immutable and
        ``archive_sha256`` / ``archive_bytes`` / ``manifest_envelope``
        are populated.
        """
        self._assert_writable()
        manifest = build_manifest(
            export_id=self.export_id,
            org_id=org_id,
            profile=profile,
            audit_period_start=audit_period_start,
            audit_period_end=audit_period_end,
            built_at=built_at,
            signer_key_id=signer.key_id,
            artifacts=[
                {
                    "path": e.path,
                    "sha256": e.sha256,
                    "bytes": e.size_bytes,
                    "controls": e.controls,
                }
                for e in self._entries
            ],
            artifact_schema_versions=dict(self.artifact_schema_versions),
        )
        envelope = sign_manifest(manifest, signer)
        # Persist both the DSSE envelope (authoritative) and a
        # human-readable copy of the manifest so a reviewer can skim
        # the archive without running the verify CLI.
        self._zip.writestr(
            "manifest.dsse.json",
            json.dumps(envelope.model_dump(mode="json"), indent=2, sort_keys=True),
        )
        self._zip.writestr(
            "manifest.json",
            json.dumps(manifest, indent=2, sort_keys=True),
        )
        self._zip.close()
        self._sealed = True
        self.manifest_envelope = envelope

        # Compute archive-level hash AFTER the file is closed — we want
        # the hash of the final on-disk bytes, not of the in-flight
        # writer state.
        sha = hashlib.sha256()
        size = 0
        with self.archive_path.open("rb") as fp:
            for chunk in iter(lambda: fp.read(64 * 1024), b""):
                sha.update(chunk)
                size += len(chunk)
        self.archive_sha256 = sha.hexdigest()
        self.archive_bytes = size

    # ── Internal ───────────────────────────────────────────────────

    def _assert_writable(self) -> None:
        if self._sealed:
            msg = "bundle is already sealed; writes would invalidate the manifest"
            raise BundleAlreadySealedError(msg)
