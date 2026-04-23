"""Placeholder profile builder.

Used by every profile until the real per-profile builder ships. Writes
two artifacts:

- ``README.md`` — human-readable verification instructions + profile
  status ("builder scoped, not yet implemented").
- ``PLACEHOLDER.txt`` — machine-readable marker with profile id and
  range so a downstream tool scanning the bundle can tell it's not
  real evidence.

The bundle is still a fully valid signed export: the manifest commits
to these two files, the DSSE signature verifies, and the archive
roundtrips. What it *isn't* is profile-specific evidence — that's
shipped in the follow-on sprint items (SOC 2 / EU AI Act / NIST).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime
    import uuid

    from common.compliance.bundle import ComplianceExportBundle

_README_TEMPLATE = """\
# AI Identity compliance export — {profile}

**Export id:** {export_id}
**Organization id:** {org_id}
**Audit period:** {period_start} → {period_end}
**Built:** {built_at}

---

## Status: foundation placeholder

This bundle was produced by the export foundation pipeline — the
manifest is signed and the archive is verifiable — but the
per-profile evidence builder for `{profile}` is not yet implemented.

Real artifacts will include the files listed in
`docs/compliance/export-profiles.md` for this framework. Ship order:

- SOC 2 TSC 2017 (#3 in the breakdown)
- EU AI Act 2024 (#4 — uses `agent.eu_ai_act_risk_class`)
- NIST AI RMF 1.0 (#5)

Until then, this bundle is suitable for:

- Integration-testing your export pipeline end-to-end
- Verifying signature + hash chain against AI Identity's JWKS
- Confirming the manifest payloadType is
  `application/vnd.ai-identity.export-manifest+json`

## Verifying this bundle

1. Extract the archive.
2. Open `manifest.dsse.json` — a DSSE envelope per SLSA/SSLsec.
3. Base64-decode `payload` to get the canonical manifest JSON.
4. Fetch the public key from
   `https://<your-host>/.well-known/ai-identity-public-keys.json`
   using the `signer_key_id` field.
5. Verify the DSSE signature over `PAE(payloadType, payload)`.
6. For each `artifacts[i]`, compute SHA-256 of the extracted file and
   compare to the manifest entry.

The `cli/ai_identity_verify.py` tool will grow an `export` subcommand
in the follow-on sprint.
"""

_PLACEHOLDER_TXT = """\
This is a foundation-only export bundle. No profile-specific evidence
has been collected yet. See README.md.
"""


def build_placeholder_bundle(
    bundle: ComplianceExportBundle,
    *,
    profile: str,
    org_id: uuid.UUID,
    export_id: uuid.UUID,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
    built_at: datetime.datetime,
) -> None:
    """Populate ``bundle`` with the placeholder artifacts.

    Caller is responsible for ``bundle.seal(...)`` — the builder only
    writes content. Keeping seal out of here means the orchestrator
    can add whole-job-level facts (e.g. guardrail counts) before
    sealing, once we have them.
    """
    bundle.write_text(
        "README.md",
        _README_TEMPLATE.format(
            profile=profile,
            export_id=export_id,
            org_id=org_id,
            period_start=audit_period_start.isoformat(),
            period_end=audit_period_end.isoformat(),
            built_at=built_at.isoformat(),
        ),
    )
    bundle.write_text("PLACEHOLDER.txt", _PLACEHOLDER_TXT)
