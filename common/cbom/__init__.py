"""Cryptographic Bill of Materials (CBOM) for AI Identity.

Emits a CycloneDX 1.6 CBOM enumerating every cryptographic asset across the
signing/verification/integrity surfaces of the platform. See generator.py.

Import the builder directly from the submodule to keep `python -m
common.cbom.generator` warning-free:

    from common.cbom.generator import build_cbom
"""
