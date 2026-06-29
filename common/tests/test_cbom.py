"""Guards for the Cryptographic Bill of Materials (CBOM).

Two jobs:
  1. Structural sanity — the document is well-formed CycloneDX 1.6 with the
     crypto-asset shape we promise downstream consumers (IBM / CoSAI / OCSF).
  2. Drift — the committed cbom.json equals freshly generated output, so the
     artifact can never silently fall behind the generator (the source of
     truth). If this fails, run `python -m common.cbom.generator`.

Every crypto-asset must cite at least one file:line occurrence — the CBOM is
an attestation, and a claim with no location in the codebase is not one we
want to ship.
"""

from pathlib import Path

from common.cbom.generator import CBOM_PATH, build_cbom, serialize

_VALID_PRIMITIVES = {"signature", "hash", "mac", "ae", "drbg", "pke", "kem", "kdf"}


def test_committed_cbom_matches_generator():
    """The checked-in artifact must match the generator byte-for-byte."""
    assert CBOM_PATH.exists(), "cbom.json missing — run `python -m common.cbom.generator`"
    assert CBOM_PATH.read_text() == serialize(build_cbom()), (
        "cbom.json is stale — run `python -m common.cbom.generator` to regenerate."
    )


def test_cbom_is_cyclonedx_1_6():
    bom = build_cbom()
    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.6"
    assert isinstance(bom["components"], list) and bom["components"]


def test_crypto_assets_are_well_formed():
    bom = build_cbom()
    crypto = [c for c in bom["components"] if c["type"] == "cryptographic-asset"]
    assert crypto, "expected at least one cryptographic-asset component"

    seen_refs = set()
    for c in crypto:
        ref = c["bom-ref"]
        assert ref not in seen_refs, f"duplicate bom-ref {ref}"
        seen_refs.add(ref)

        cp = c["cryptoProperties"]
        assert cp["assetType"] == "algorithm"
        assert cp["algorithmProperties"]["primitive"] in _VALID_PRIMITIVES
        assert cp["algorithmProperties"]["cryptoFunctions"]

        # An attestation with no location is not a claim we ship.
        occurrences = c["evidence"]["occurrences"]
        assert occurrences, f"{ref} has no occurrences"
        for occ in occurrences:
            loc = occ["location"]
            path, _, line = loc.partition(":")
            assert line.isdigit(), f"{ref} occurrence not file:line: {loc}"
            p = Path(path)
            assert p.exists(), f"{ref} cites missing file: {path}"
            n_lines = len(p.read_text().splitlines())
            assert 1 <= int(line) <= n_lines, (
                f"{ref} cites {loc} but {path} has {n_lines} lines — stale line number"
            )


def test_dependency_refs_resolve():
    """Every dependsOn edge must point at a real component bom-ref."""
    bom = build_cbom()
    refs = {c["bom-ref"] for c in bom["components"]}
    for dep in bom["dependencies"]:
        assert dep["ref"] in refs
        for target in dep["dependsOn"]:
            assert target in refs, f"dangling dependency {target}"


def test_pqc_asset_present_and_honest():
    """The ML-DSA-87 asset must be marked verify-only / opt-in — no overclaim."""
    bom = build_cbom()
    mldsa = next(c for c in bom["components"] if c.get("bom-ref") == "crypto/ml-dsa-87")
    funcs = mldsa["cryptoProperties"]["algorithmProperties"]["cryptoFunctions"]
    assert funcs == ["verify"], "ML-DSA-87 must be verify-only (no issuance)"
    status = next(p["value"] for p in mldsa["properties"] if p["name"] == "ai-identity:status")
    assert "verify-only" in status and "no issuance" in status
