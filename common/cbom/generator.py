"""Generate the AI Identity Cryptographic Bill of Materials (CBOM).

Output format: CycloneDX 1.6 (the OWASP standard with first-class
``cryptographic-asset`` components). We chose CycloneDX because CISA's
forthcoming "CBOM minimum elements" (~Dec 2026, per Sprint 17 #424) is being
built around it — so aligning now keeps "revisit when CISA lands" a tweak,
not a rewrite — and because it's the format a partner (IBM / CoSAI WS4 /
OCSF) can ingest with existing tooling.

This is a *curated* inventory maintained in code, not AST-derived. Crypto
usage is not reliably auto-detectable, and a CBOM is a deliberate attestation
of what the system uses — so the source of truth is the structured data below,
each entry carrying file:line ``occurrences`` so a reviewer can verify every
claim against the codebase. ``common/tests/test_cbom.py`` guards the committed
``cbom.json`` against drift from this generator.

Deterministic by construction: no timestamp or serialNumber (both optional in
CycloneDX), sorted keys, stable bom-refs — so regenerating never churns the
committed artifact.

Scope: cryptographic *algorithms, key material, and the libraries that
implement them*. Encodings (base64/base64url) and JSON canonicalization
(RFC 8785 / JCS) are not algorithms; JCS is recorded as a dependency of the
signature assets because the canonical pre-image is security-relevant, but it
is not listed as a crypto-asset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CBOM_PATH = Path(__file__).with_name("cbom.json")

SPEC_VERSION = "1.6"

# --- Implementing libraries (CycloneDX `library` components) ----------------
# Versions are the pins in mandate/api/gateway requirements.txt as of writing.
LIBRARIES: list[dict[str, Any]] = [
    {
        "bom-ref": "lib/cryptography",
        "name": "cryptography",
        "version": "46.0.5",
        "purl": "pkg:pypi/cryptography@46.0.5",
        "description": "ECDSA P-256 sign/verify, EC key handling, Fernet AEAD.",
    },
    {
        "bom-ref": "lib/google-cloud-kms",
        "name": "google-cloud-kms",
        "version": "3.12.0",
        "purl": "pkg:pypi/google-cloud-kms@3.12.0",
        "description": "GCP Cloud KMS asymmetric signing (ECDSA P-256) + public-key fetch.",
    },
    {
        "bom-ref": "lib/liboqs-python",
        "name": "liboqs-python",
        "version": "0.15.0",
        "purl": "pkg:pypi/liboqs-python@0.15.0",
        "description": "Open Quantum Safe binding; ML-DSA-87 verify path (verify only).",
    },
    {
        "bom-ref": "lib/pyjwt",
        "name": "PyJWT",
        "version": "2.10.1",
        "purl": "pkg:pypi/pyjwt@2.10.1",
        "description": "RS256 verification of Clerk user-session JWTs (not agent auth).",
    },
    {
        "bom-ref": "lib/rfc8785",
        "name": "rfc8785",
        "version": "0.1.4",
        "purl": "pkg:pypi/rfc8785@0.1.4",
        "description": "RFC 8785 JSON Canonicalization Scheme — deterministic signature pre-image.",
    },
]

# Python standard library backs SHA-256/HMAC/CSPRNG; no pinned version.
_STDLIB = "Python standard library (hashlib / hmac / secrets)"


# --- Cryptographic assets (CycloneDX `cryptographic-asset` components) ------
# Each carries algorithmProperties + file:line occurrences + AI-Identity
# properties (surface / purpose / key custody / status / implementation).
CRYPTO_ASSETS: list[dict[str, Any]] = [
    {
        "bom-ref": "crypto/ecdsa-p256-sha256",
        "name": "ECDSA P-256 with SHA-256",
        "primitive": "signature",
        "curve": "P-256",
        "cryptoFunctions": ["sign", "verify"],
        "nistQuantumSecurityLevel": 0,
        "classicalSecurityLevel": 128,
        "dependsOn": ["lib/cryptography", "lib/google-cloud-kms", "lib/rfc8785"],
        "occurrences": [
            "mandate/app/signing.py:162",  # sign_mandate (classical)
            "mandate/app/signing.py:303",  # verify_signature ECDSA path
            "common/forensic/signer.py:190",  # local checkpoint signer
            "common/forensic/anchor_checkpoint.py:154",  # checkpoint sign
        ],
        "properties": {
            "surface": "Mandate signing; Evidence Anchor checkpoint signing",
            "purpose": "Sign/verify mandates and signed Merkle checkpoints (DSSE envelopes)",
            "keyCustody": "GCP Cloud KMS (HSM-backed) in production; local PEM in dev/test",
            "encoding": "IEEE P1363 (mandate) / DER (checkpoint); RFC 8785 canonical pre-image",
            "status": "live",
            "implementation": "cryptography 46.0.5; google-cloud-kms 3.12.0",
        },
    },
    {
        "bom-ref": "crypto/ml-dsa-87",
        "name": "ML-DSA-87 (FIPS 204)",
        "primitive": "signature",
        "parameterSetIdentifier": "ML-DSA-87",
        "cryptoFunctions": ["verify"],
        "nistQuantumSecurityLevel": 5,
        "classicalSecurityLevel": 256,
        "dependsOn": ["lib/liboqs-python", "lib/rfc8785"],
        "occurrences": [
            "mandate/app/signing.py:259",  # ml-dsa-87 branch in verify_signature
        ],
        "properties": {
            "surface": "Mandate verification (post-quantum slot)",
            "purpose": "Verify ML-DSA-87 signatures on hybrid or PQC-only mandates",
            "keyCustody": "settings.forensic_mldsa_public_key (trusted public key; verify only)",
            "encoding": "raw message signing (no prehash); RFC 8785 canonical pre-image",
            "status": "verify-only, opt-in (inert until a trusted PQC key is configured); no issuance",
            "implementation": "liboqs-python 0.15.0 (liboqs / Open Quantum Safe)",
        },
    },
    {
        "bom-ref": "crypto/hmac-sha256",
        "name": "HMAC-SHA256",
        "primitive": "mac",
        "cryptoFunctions": ["tag", "verify"],
        "classicalSecurityLevel": 256,
        "dependsOn": [],
        "occurrences": [
            "common/audit/writer.py:111",  # audit hash chain
            "common/auth/internal.py:146",  # internal service-to-service auth
        ],
        "properties": {
            "surface": "Audit log integrity chain (global + per-org); internal service auth",
            "purpose": "Tamper-evident audit chaining; mutual API<->Gateway authentication",
            "keyCustody": "settings.audit_hmac_key (global) or org.forensic_verify_key (per-org); "
            "settings.internal_service_key (service auth)",
            "verification": "secret-dependent — verifier needs the HMAC key (unlike the "
            "ECDSA/Merkle public-verifiability path)",
            "status": "live",
            "implementation": _STDLIB,
        },
    },
    {
        "bom-ref": "crypto/sha-256",
        "name": "SHA-256",
        "primitive": "hash",
        "cryptoFunctions": ["digest"],
        "classicalSecurityLevel": 128,
        "dependsOn": [],
        "occurrences": [
            "mandate/app/signing.py:133",  # payload digest before ECDSA
            "common/auth/keys.py:46",  # agent key hashing for DB lookup
            "common/forensic/merkle.py:38",  # Merkle leaf hashing
        ],
        "properties": {
            "surface": "ECDSA payload digest; agent-key storage hash; Merkle tree; HMAC input",
            "purpose": "Pre-image digest, key fingerprinting, content-addressed integrity",
            "status": "live",
            "implementation": _STDLIB,
        },
    },
    {
        "bom-ref": "crypto/merkle-rfc6962",
        "name": "RFC 6962 Merkle tree (domain-separated SHA-256)",
        "primitive": "hash",
        "cryptoFunctions": ["digest"],
        "classicalSecurityLevel": 128,
        "dependsOn": [],
        "occurrences": [
            "common/forensic/merkle.py:38",  # leaf hash SHA-256(0x00||data)
            "common/forensic/merkle.py:43",  # node hash SHA-256(0x01||l||r)
        ],
        "properties": {
            "surface": "Evidence Anchor inclusion proofs",
            "purpose": "Public-key-free inclusion proofs over checkpointed audit events",
            "construction": "leaf=SHA-256(0x00||data); node=SHA-256(0x01||left||right)",
            "status": "live",
            "implementation": _STDLIB,
        },
    },
    {
        "bom-ref": "crypto/rs256",
        "name": "RSASSA-PKCS1-v1_5 with SHA-256 (RS256)",
        "primitive": "signature",
        "cryptoFunctions": ["verify"],
        "nistQuantumSecurityLevel": 0,
        "dependsOn": ["lib/pyjwt"],
        "occurrences": [
            "api/app/auth.py:59",  # Clerk JWT verification (jwt.decode)
        ],
        "properties": {
            "surface": "User-session authentication (Clerk JWTs)",
            "purpose": "Verify Clerk-issued user login tokens — NOT agent/runtime key auth",
            "keyCustody": "Clerk JWKS (rotated by Clerk; key size set by issuer)",
            "status": "live",
            "implementation": "PyJWT 2.10.1",
        },
    },
    {
        "bom-ref": "crypto/fernet-aes128-cbc-hmac",
        "name": "Fernet (AES-128-CBC + HMAC-SHA256)",
        "primitive": "ae",
        "cryptoFunctions": ["encrypt", "decrypt"],
        "classicalSecurityLevel": 128,
        "dependsOn": ["lib/cryptography"],
        "occurrences": [
            "common/crypto/fernet.py:44",  # Fernet(key)
        ],
        "properties": {
            "surface": "Upstream credential encryption at rest",
            "purpose": "Authenticated encryption of stored upstream API keys",
            "keyCustody": "settings.credential_encryption_key (Fernet key; base64 32 bytes)",
            "status": "live",
            "implementation": "cryptography 46.0.5 (cryptography.fernet)",
        },
    },
    {
        "bom-ref": "crypto/csprng-token",
        "name": "CSPRNG token generation (secrets.token_urlsafe)",
        "primitive": "drbg",
        "cryptoFunctions": ["keygen"],
        "classicalSecurityLevel": 256,
        "dependsOn": [],
        "occurrences": [
            "common/auth/keys.py:19",  # secrets.token_urlsafe(32)
        ],
        "properties": {
            "surface": "Agent API key generation (aid_sk_ runtime / aid_admin_ admin)",
            "purpose": "Generate high-entropy bearer keys; only the SHA-256 hash is stored",
            "status": "live",
            "implementation": _STDLIB,
        },
    },
]


def _algorithm_properties(asset: dict[str, Any]) -> dict[str, Any]:
    """Build the CycloneDX cryptoProperties.algorithmProperties block."""
    algo: dict[str, Any] = {
        "primitive": asset["primitive"],
        "cryptoFunctions": list(asset["cryptoFunctions"]),
    }
    if "curve" in asset:
        algo["curve"] = asset["curve"]
    if "parameterSetIdentifier" in asset:
        algo["parameterSetIdentifier"] = asset["parameterSetIdentifier"]
    if "nistQuantumSecurityLevel" in asset:
        algo["nistQuantumSecurityLevel"] = asset["nistQuantumSecurityLevel"]
    if "classicalSecurityLevel" in asset:
        algo["classicalSecurityLevel"] = asset["classicalSecurityLevel"]
    return algo


def _ai_properties(props: dict[str, str]) -> list[dict[str, str]]:
    """Render the AI-Identity property bag as sorted CycloneDX name/value pairs."""
    return [{"name": f"ai-identity:{key}", "value": value} for key, value in sorted(props.items())]


def _crypto_component(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "cryptographic-asset",
        "bom-ref": asset["bom-ref"],
        "name": asset["name"],
        "cryptoProperties": {
            "assetType": "algorithm",
            "algorithmProperties": _algorithm_properties(asset),
        },
        "evidence": {
            "occurrences": [{"location": loc} for loc in asset["occurrences"]],
        },
        "properties": _ai_properties(asset["properties"]),
    }


def _library_component(lib: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "library",
        "bom-ref": lib["bom-ref"],
        "name": lib["name"],
        "version": lib["version"],
        "purl": lib["purl"],
        "description": lib["description"],
    }


def build_cbom() -> dict[str, Any]:
    """Assemble the full CycloneDX 1.6 CBOM document (deterministic)."""
    components = [_library_component(lib) for lib in LIBRARIES]
    components += [_crypto_component(asset) for asset in CRYPTO_ASSETS]

    dependencies = [
        {"ref": asset["bom-ref"], "dependsOn": list(asset["dependsOn"])}
        for asset in CRYPTO_ASSETS
        if asset["dependsOn"]
    ]

    return {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": "app/ai-identity",
                "name": "ai-identity",
                "description": "Verifiable identity, governance, and forensics for AI agents.",
            },
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "ai-identity-cbom-generator",
                        "description": "common/cbom/generator.py — curated, code-grounded CBOM.",
                    }
                ]
            },
            "properties": [
                {
                    "name": "ai-identity:scope",
                    "value": "Cryptographic algorithms, key material, and implementing "
                    "libraries across mandate, Evidence Anchor, gateway/agent-key, audit "
                    "chain, and credential-encryption surfaces.",
                },
                {
                    "name": "ai-identity:exclusions",
                    "value": "base64/base64url (encoding) are not crypto assets; RFC 8785 "
                    "(JCS) is recorded as a dependency of signature assets, not a crypto asset.",
                },
                {
                    "name": "ai-identity:determinism",
                    "value": "No timestamp/serialNumber by design; regenerate via "
                    "python -m common.cbom.generator. Drift-guarded by common/tests/test_cbom.py.",
                },
            ],
        },
        "components": components,
        "dependencies": dependencies,
    }


def serialize(bom: dict[str, Any]) -> str:
    """Stable JSON serialization (sorted keys, trailing newline)."""
    return json.dumps(bom, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the AI Identity CBOM (CycloneDX 1.6).")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed cbom.json differs from freshly generated output.",
    )
    args = parser.parse_args()

    generated = serialize(build_cbom())

    if args.check:
        current = CBOM_PATH.read_text() if CBOM_PATH.exists() else ""
        if current != generated:
            raise SystemExit(
                f"{CBOM_PATH} is out of date — run `python -m common.cbom.generator` to regenerate."
            )
        print(f"{CBOM_PATH.name} is up to date.")
        return

    CBOM_PATH.write_text(generated)
    print(f"Wrote {CBOM_PATH} ({len(build_cbom()['components'])} components).")


if __name__ == "__main__":
    main()
