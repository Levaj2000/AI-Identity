"""Spike tests for Workload Identity Federation (#422).

A locally-generated RSA keypair stands in for an external IdP: we mint OIDC
assertions with it, hand them to the federation exchange with a key resolver
that returns the local public key (no network), and assert that a valid
assertion yields a short-lived AI Identity token while every tampering /
expiry / audience / allowlist failure is rejected.
"""

import datetime

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from common.auth.federation import (
    AI_IDENTITY_TOKEN_ISSUER,
    FederatedIssuer,
    FederationError,
    federate,
    issue_token,
    verify_issued_token,
)

ISSUER_URL = "https://idp.example.com"
AUDIENCE = "https://ai-identity.co/agents"
AI_SECRET = "spike-signing-secret-not-for-prod"


@pytest.fixture(scope="module")
def rsa_keys():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = (
        priv.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return priv_pem, pub_pem


@pytest.fixture
def resolver(rsa_keys):
    _, pub_pem = rsa_keys
    return lambda _token: pub_pem


def _make_assertion(rsa_keys, **overrides) -> str:
    priv_pem, _ = rsa_keys
    now = datetime.datetime.now(datetime.UTC)
    claims = {
        "iss": ISSUER_URL,
        "aud": AUDIENCE,
        "sub": "spiffe://example.com/ns/prod/sa/billing-agent",
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(claims, priv_pem, algorithm="RS256")


def _issuer(**overrides) -> FederatedIssuer:
    base = {
        "issuer": ISSUER_URL,
        "jwks_uri": f"{ISSUER_URL}/.well-known/jwks.json",
        "audience": AUDIENCE,
        "subject_to_agent": {"spiffe://example.com/ns/prod/sa/billing-agent": "agt_billing"},
        "default_scopes": ("read:audit",),
    }
    base.update(overrides)
    return FederatedIssuer(**base)


def test_happy_path_issues_short_lived_token(rsa_keys, resolver):
    grant = federate(_make_assertion(rsa_keys), _issuer(), secret=AI_SECRET, key_resolver=resolver)
    assert grant.agent_id == "agt_billing"
    assert grant.scopes == ("read:audit",)

    # The minted token is a real, verifiable, short-lived AI Identity token.
    claims = verify_issued_token(grant.token, secret=AI_SECRET)
    assert claims["sub"] == "agt_billing"
    assert claims["iss"] == AI_IDENTITY_TOKEN_ISSUER
    assert claims["token_use"] == "federated"
    assert grant.expires_at > datetime.datetime.now(datetime.UTC)


def test_agent_id_claim_mode(rsa_keys, resolver):
    """When the issuer carries the agent id in a claim, use it directly."""
    assertion = _make_assertion(rsa_keys, ai_identity_agent="agt_from_claim")
    issuer = _issuer(agent_id_claim="ai_identity_agent", subject_to_agent={})
    grant = federate(assertion, issuer, secret=AI_SECRET, key_resolver=resolver)
    assert grant.agent_id == "agt_from_claim"


def test_tampered_assertion_rejected(rsa_keys, resolver):
    assertion = _make_assertion(rsa_keys)
    tampered = assertion[:-3] + ("aaa" if assertion[-3:] != "aaa" else "bbb")
    with pytest.raises(FederationError):
        federate(tampered, _issuer(), secret=AI_SECRET, key_resolver=resolver)


def test_expired_assertion_rejected(rsa_keys, resolver):
    now = datetime.datetime.now(datetime.UTC)
    expired = _make_assertion(rsa_keys, exp=int((now - datetime.timedelta(minutes=1)).timestamp()))
    with pytest.raises(FederationError):
        federate(expired, _issuer(), secret=AI_SECRET, key_resolver=resolver)


def test_wrong_audience_rejected(rsa_keys, resolver):
    assertion = _make_assertion(rsa_keys, aud="https://someone-else.example/api")
    with pytest.raises(FederationError):
        federate(assertion, _issuer(), secret=AI_SECRET, key_resolver=resolver)


def test_wrong_issuer_rejected(rsa_keys, resolver):
    assertion = _make_assertion(rsa_keys, iss="https://evil-idp.example.com")
    with pytest.raises(FederationError):
        federate(assertion, _issuer(), secret=AI_SECRET, key_resolver=resolver)


def test_subject_not_in_allowlist_rejected(rsa_keys, resolver):
    issuer = _issuer(allowed_subjects=frozenset({"spiffe://example.com/ns/prod/sa/other"}))
    with pytest.raises(FederationError):
        federate(_make_assertion(rsa_keys), issuer, secret=AI_SECRET, key_resolver=resolver)


def test_unmapped_subject_rejected(rsa_keys, resolver):
    issuer = _issuer(subject_to_agent={})  # no mapping, no agent_id_claim
    with pytest.raises(FederationError):
        federate(_make_assertion(rsa_keys), issuer, secret=AI_SECRET, key_resolver=resolver)


def test_issued_token_tamper_rejected():
    grant = issue_token("agt_x", secret=AI_SECRET, scopes=("read:audit",))
    with pytest.raises(FederationError):
        verify_issued_token(grant.token + "x", secret=AI_SECRET)


def test_issued_token_wrong_secret_rejected():
    grant = issue_token("agt_x", secret=AI_SECRET)
    with pytest.raises(FederationError):
        verify_issued_token(grant.token, secret="a-different-secret")
