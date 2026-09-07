#!/usr/bin/env python3
"""Assemble the shareable evidence package — the artifacts we hand to
researchers, working-group members, and prospects who ask "show me the wire".

Everything included is already public in this repository. The script exists so
the same package ships every time (same files, same index, same ordering)
instead of being re-assembled by hand per conversation.

    python3 scripts/build_evidence_package.py                    # -> dist/
    python3 scripts/build_evidence_package.py --out-dir /tmp/x   # elsewhere

Produces `ai-identity-evidence-package-<YYYY-MM-DD>.zip` containing the OCSF
reference bundle, the attestation-finding sample with its offline verifier, the
trust-base inventory sample, and the two WS4 documents that explain them —
plus a README indexing the lot with a suggested reading order.

Stdlib only. Refuses to run if any source path is missing, so a moved file is
caught here rather than by the recipient.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPING_DIR = REPO_ROOT / "docs" / "cosai-ws4-ocsf-mapping"
STRATEGY_DIR = REPO_ROOT / "docs" / "strategy"

# (source, destination-inside-package). Directories are copied whole.
CONTENTS: list[tuple[Path, str]] = [
    (MAPPING_DIR / "ocsf-log-reference-bundle", "01-ocsf-log-reference-bundle"),
    (MAPPING_DIR / "attestation-finding-sample", "02-attestation-finding-sample"),
    (MAPPING_DIR / "trust-base-inventory-sample", "03-trust-base-inventory-sample"),
    (
        MAPPING_DIR / "evidence-contract-ocsf-mapping.md",
        "04-evidence-contract-ocsf-mapping.md",
    ),
    (
        STRATEGY_DIR / "cosai-ws4-cross-runtime-visibility.md",
        "05-cross-runtime-agent-visibility.md",
    ),
]

INDEX = """# AI Identity — Evidence Package

Real telemetry and verification tooling from the AI Identity gateway, plus the
two working-group documents that explain what the records are for. Everything
here is public; the source of truth for each file is
<https://github.com/Levaj2000/AI-Identity>.

Built {date}.

## Suggested reading order

**1. `01-ocsf-log-reference-bundle/`** — start with `README.md`, then read
`production-ocsf-excerpt.ocsf.ndjson` alongside it. Seven consecutive events
from one agent's lifecycle: created, denied (no policy), allowed, denied
(privileged op), key rotation, decommissioned, denied (post-decommission).
Each event is an OCSF API Activity record (`class_uid` 6003) under the
`ai_operation` + `record_integrity` profiles. `production-ocsf-full-export.ocsf.ndjson`
is the unabridged org chain if you want volume rather than a narrative.

This is what "reconstructing an agentic workflow" looks like on the wire —
each event's `prev_event.fingerprint.value` equals the previous event's
`fingerprint.value`, so the sequence is a chain rather than a pile of logs.

**2. `02-attestation-finding-sample/`** — the offline-verification story, and
the part worth running rather than reading. `verify_finding.py` is a standalone
verifier: it re-implements RFC 6962 Merkle proofs and DSSE signature checking
in-file and imports nothing from the system that produced the evidence.

```
pip install cryptography
cd 02-attestation-finding-sample
python3 verify_finding.py                      # both variants verify
python3 verify_finding.py --tamper substitute  # edit an event, hash rewritten consistently
python3 verify_finding.py --prove 3            # prove one event's inclusion, O(log N)
```

The `--tamper substitute` run is the interesting one: it shows a finding whose
references carry only event IDs verifying *falsely* against edited content,
while the same finding with a content hash per reference catches the edit at
the exact index. That is the argument being made upstream in
[ocsf/ocsf-schema#1689](https://github.com/ocsf/ocsf-schema/pull/1689).

**3. `03-trust-base-inventory-sample/`** — what an agent *declared* it would
use versus what it *executed*, as a chained admission/closure pair. Divergence
between the two is a diff a consumer computes; an admission with no closure is
a structurally checkable gap. Draft class behind it:
[ocsf/ocsf-schema#1724](https://github.com/ocsf/ocsf-schema/issues/1724).

**4. `04-evidence-contract-ocsf-mapping.md`** — the field-by-field map: what an
evidence record must carry to reconstruct an agent decision, where each field
lands in OCSF v1.9.0, and — the useful half — which fields have no home in the
schema yet. Note the "Producer gaps" section, which names where our own export
falls short of the mapping.

**5. `05-cross-runtime-agent-visibility.md`** — what survives when an agent
crosses into a runtime you do not control. Separates three problems that get
blurred together: authority continuity, correlation continuity, and emission.
The honest limit is stated first: you cannot instrument a runtime that emits
nothing.

## A note on the data

The telemetry is from a demo/QA org — `demo-agent-*` and `QA-*` agents, one
synthetic user, opaque UUID identifiers. No customer data, PII, or secrets.
Two integrity mechanisms appear in each event and they differ on purpose: the
hash chain is HMAC-SHA-256 (keyed, so recomputation needs the org's key), while
the per-event signature is ECDSA-P256 and publicly verifiable against the JWKS
at <https://api.ai-identity.co/.well-known/ai-identity-public-keys.json>.

Questions welcome — jeff@ai-identity.co.
"""


def build(out_dir: Path, date: str) -> Path:
    stage = out_dir / f"ai-identity-evidence-package-{date}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    missing = [str(src.relative_to(REPO_ROOT)) for src, _ in CONTENTS if not src.exists()]
    if missing:
        sys.exit("missing source paths (moved or renamed?):\n  " + "\n  ".join(missing))

    for src, dest in CONTENTS:
        target = stage / dest
        if src.is_dir():
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)

    (stage / "README.md").write_text(INDEX.format(date=date))

    archive = out_dir / f"{stage.name}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(out_dir))
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="where to write the staged directory and zip (default: ./dist)",
    )
    parser.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="date stamp for the package name (default: today)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    archive = build(args.out_dir, args.date)
    size_kb = archive.stat().st_size / 1024
    print(f"{archive}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
