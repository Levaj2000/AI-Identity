"""Tests for hardware attestation at agent registration (#423).

A local CA + client certs stand in for a real mTLS deployment. We verify the
happy path (cert chains to the trusted CA, within validity → verified) and the
honest-negative paths (untrusted CA, expired, no CA configured, garbage) where
the attestation is still *recorded* with its identity binding but not trusted.
Also checks the OCSF mapper surfaces workload attestation in ``unmapped``,
separate from the record-integrity ``attestation`` object.
"""

import datetime
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from common.attestation import (
    AttestationType,
    HardwareAttestation,
    verify_attestation,
    verify_mtls_attestation,
)
from common.ocsf.api_activity import audit_log_to_ocsf

_NOW = datetime.datetime.now(datetime.UTC)


def _key():
    return ec.generate_private_key(ec.SECP256R1())


def _ca(key):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Workload CA")])
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(_NOW - datetime.timedelta(days=1))
        .not_valid_after(_NOW + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )


def _leaf(leaf_key, ca_cert, ca_key, *, spiffe=None, not_before=None, not_after=None):
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "billing-agent")]))
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before or _NOW - datetime.timedelta(hours=1))
        .not_valid_after(not_after or _NOW + datetime.timedelta(days=365))
    )
    if spiffe:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(spiffe)]),
            critical=False,
        )
    return builder.sign(ca_key, hashes.SHA256())


def _pem(cert):
    return cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture(scope="module")
def ca():
    ca_key = _key()
    return ca_key, _ca(ca_key)


def test_valid_cert_chaining_to_trusted_ca_is_verified(ca):
    ca_key, ca_cert = ca
    leaf = _leaf(_key(), ca_cert, ca_key, spiffe="spiffe://example.org/ns/prod/sa/billing")
    r = verify_mtls_attestation(_pem(leaf), trusted_ca_pem=_pem(ca_cert))
    assert r.verified is True
    assert r.subject == "spiffe://example.org/ns/prod/sa/billing"
    assert r.public_key_sha256 and len(r.public_key_sha256) == 64
    assert "trusted CA" in r.reason


def test_untrusted_ca_records_but_does_not_verify(ca):
    ca_key, ca_cert = ca
    # Leaf signed by a *different* CA than the one we trust.
    other_key = _key()
    other_ca = _ca(other_key)
    leaf = _leaf(_key(), other_ca, other_key)
    r = verify_mtls_attestation(_pem(leaf), trusted_ca_pem=_pem(ca_cert))
    assert r.verified is False
    # Either name-chaining or signature fails depending on issuer name — both
    # mean "not trusted"; the reason names the trusted CA in both branches.
    assert "trusted CA" in r.reason
    # Identity binding is still extracted (recorded, just not trusted).
    assert r.public_key_sha256 and r.subject


def test_expired_cert_is_not_verified(ca):
    ca_key, ca_cert = ca
    leaf = _leaf(
        _key(),
        ca_cert,
        ca_key,
        not_before=_NOW - datetime.timedelta(days=10),
        not_after=_NOW - datetime.timedelta(days=1),
    )
    r = verify_mtls_attestation(_pem(leaf), trusted_ca_pem=_pem(ca_cert))
    assert r.verified is False
    assert "validity window" in r.reason


def test_no_trusted_ca_records_unverified(ca):
    ca_key, ca_cert = ca
    leaf = _leaf(_key(), ca_cert, ca_key)
    r = verify_mtls_attestation(_pem(leaf), trusted_ca_pem=None)
    assert r.verified is False
    assert "no trusted CA" in r.reason
    assert r.public_key_sha256  # still recorded the binding


def test_garbage_evidence_fails_cleanly():
    r = verify_mtls_attestation("not a certificate", trusted_ca_pem=None)
    assert r.verified is False
    assert "could not parse" in r.reason


def test_dispatch_unimplemented_type_is_honest():
    att = HardwareAttestation(attestation_type=AttestationType.tpm_quote, evidence="x")
    r = verify_attestation(att)
    assert r.verified is False
    assert "not yet implemented" in r.reason


def test_audit_scalars_are_flat_and_safe(ca):
    ca_key, ca_cert = ca
    leaf = _leaf(_key(), ca_cert, ca_key, spiffe="spiffe://example.org/ns/prod/sa/billing")
    r = verify_mtls_attestation(_pem(leaf), trusted_ca_pem=_pem(ca_cert))
    scalars = r.audit_scalars()
    assert scalars["attestation_type"] == "mtls_cert"
    assert scalars["attestation_verified"] is True
    assert scalars["attestation_subject"] == "spiffe://example.org/ns/prod/sa/billing"
    # All values must be scalars (the audit sanitizer drops nested types).
    assert all(isinstance(v, (str, bool)) for v in scalars.values())


def _row(**md):
    return SimpleNamespace(
        method="POST",
        decision="allow",
        created_at=_NOW,
        correlation_id=None,
        endpoint="/api/v1/agents",
        agent_id="agt-1",
        agent_name="billing-agent",
        latency_ms=None,
        user_id=None,
        entry_hash="abc123",
        prev_hash="prev123",
        entry_hash_org=None,
        prev_hash_org=None,
        org_id=None,
        cost_estimate_usd=None,
        org_chain_seq=None,
        request_metadata=md,
    )


def test_ocsf_surfaces_workload_attestation_separate_from_integrity():
    row = _row(
        attestation_type="mtls_cert",
        attestation_verified=True,
        attestation_subject="spiffe://example.org/ns/prod/sa/billing",
        attestation_pubkey_sha256="deadbeef",
    )
    event = audit_log_to_ocsf(row)
    wa = event["unmapped"]["workload_attestation"]
    assert wa["attestation_type"] == "mtls_cert"
    assert wa["verified"] is True
    assert wa["subject"] == "spiffe://example.org/ns/prod/sa/billing"
    assert wa["public_key_sha256"] == "deadbeef"
    # Precision trap: record-integrity attestation is a SEPARATE object.
    assert event["attestation"]["entry_hash"] == "abc123"
    assert "workload_attestation" not in event["attestation"]


def test_ocsf_no_workload_attestation_when_absent():
    event = audit_log_to_ocsf(_row(policy_version=36))
    assert "workload_attestation" not in event.get("unmapped", {})
