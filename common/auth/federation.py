"""Workload Identity Federation for agent credentials — SPIKE (#422).

Problem (Insight #101): a static bearer secret (`aid_sk_...`) is an unattractive
agent credential for federated customers — it lives forever, must be stored, and
is a standing liability if leaked. Anthropic shipped Workload Identity Federation
(WIF): an agent presents a short-lived OIDC JWT minted by its own identity
provider, and receives a short-lived, scoped token in exchange — no stored
secret.

This module mirrors that exchange for AI Identity:

    OIDC assertion (from a registered IdP)
        --> verify signature + issuer + audience + expiry   (verify_assertion)
        --> map verified claims to an AI Identity agent       (resolve_agent)
        --> mint a short-lived, scoped AI Identity token      (issue_token)

It reuses the same primitive the Clerk user-auth path already uses
(`PyJWT` + JWKS, RS256). SPIKE SCOPE: this proves the end-to-end exchange with
pure, injectable functions and a self-contained signed token. It does NOT wire
HTTP routes, persistence, or issuer admin — see the design doc for what
productionizing requires. Core functions take their inputs explicitly (key
resolver, secret, clock) so the flow is testable without a network or DB.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable
from typing import Any

import jwt

# The AI Identity token this exchange mints is self-contained and short-lived
# (a signed JWT), deliberately NOT a stored `aid_sk_` key — that is the whole
# point of federation. iss identifies us as the token issuer.
AI_IDENTITY_TOKEN_ISSUER = "https://ai-identity.co"
DEFAULT_TOKEN_TTL_SECONDS = 300  # 5 minutes — short-lived by design
DEFAULT_TOKEN_ALGORITHM = "HS256"


class FederationError(Exception):
    """Raised when a federated assertion cannot be verified or mapped."""


@dataclasses.dataclass(frozen=True)
class FederatedIssuer:
    """A registered external identity provider trusted to vouch for agents.

    issuer / jwks_uri / audience are standard OIDC. The mapping fields decide
    *which* AI Identity agent a verified assertion corresponds to:

      - ``agent_id_claim`` — if set, the agent_id is read from this claim.
      - ``subject_to_agent`` — otherwise, the ``sub`` claim is looked up here.

    ``allowed_subjects`` (when set) is an explicit allowlist of acceptable
    ``sub`` values — defence in depth so a valid token from the issuer for an
    unexpected workload is still rejected.
    """

    issuer: str
    jwks_uri: str
    audience: str
    agent_id_claim: str | None = None
    subject_to_agent: dict[str, str] = dataclasses.field(default_factory=dict)
    allowed_subjects: frozenset[str] | None = None
    algorithms: tuple[str, ...] = ("RS256",)
    default_scopes: tuple[str, ...] = ()


# A key resolver maps a raw token to the verification key for its signature.
# In production this is PyJWKClient(issuer.jwks_uri).get_signing_key_from_jwt;
# tests inject a resolver returning a local public key (no network).
KeyResolver = Callable[[str], Any]


def default_key_resolver(issuer: FederatedIssuer) -> KeyResolver:
    """Production resolver: fetch the signing key from the issuer's JWKS."""

    client = jwt.PyJWKClient(issuer.jwks_uri, cache_keys=True)

    def _resolve(token: str) -> Any:
        return client.get_signing_key_from_jwt(token).key

    return _resolve


def verify_assertion(
    token: str,
    issuer: FederatedIssuer,
    key_resolver: KeyResolver,
) -> dict[str, Any]:
    """Verify an inbound OIDC assertion and return its validated claims.

    Validates the signature (against the issuer's key), and the iss / aud /
    exp claims. Requires exp and iat to be present — an assertion with no
    expiry is exactly the static-credential failure mode we are removing.
    """
    try:
        signing_key = key_resolver(token)
        return jwt.decode(
            token,
            signing_key,
            algorithms=list(issuer.algorithms),
            audience=issuer.audience,
            issuer=issuer.issuer,
            options={"require": ["exp", "iat"], "verify_aud": True, "verify_iss": True},
        )
    except jwt.InvalidTokenError as e:
        raise FederationError(f"assertion verification failed: {e}") from e


def resolve_agent(claims: dict[str, Any], issuer: FederatedIssuer) -> str:
    """Map verified claims to an AI Identity agent_id, enforcing the allowlist."""
    subject = claims.get("sub")
    if not subject:
        raise FederationError("assertion has no 'sub' claim")

    if issuer.allowed_subjects is not None and subject not in issuer.allowed_subjects:
        raise FederationError(f"subject {subject!r} is not in the issuer allowlist")

    if issuer.agent_id_claim:
        agent_id = claims.get(issuer.agent_id_claim)
        if not agent_id:
            raise FederationError(
                f"assertion missing required agent claim {issuer.agent_id_claim!r}"
            )
        return str(agent_id)

    agent_id = issuer.subject_to_agent.get(subject)
    if not agent_id:
        raise FederationError(f"no agent mapping for subject {subject!r}")
    return agent_id


@dataclasses.dataclass(frozen=True)
class FederatedGrant:
    """The result of a successful federation exchange."""

    agent_id: str
    token: str
    expires_at: datetime.datetime
    scopes: tuple[str, ...]


def issue_token(
    agent_id: str,
    *,
    secret: str,
    scopes: tuple[str, ...] = (),
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    now: datetime.datetime | None = None,
) -> FederatedGrant:
    """Mint a short-lived, scoped AI Identity token for a federated agent.

    The token is a signed JWT — self-contained and expiring — so nothing is
    stored and the credential cannot outlive its TTL. ``secret`` is the AI
    Identity token-signing secret (HS256 for the spike; an asymmetric key is
    the obvious production upgrade so verifiers need no shared secret).
    """
    if not secret:
        raise FederationError("no AI Identity token-signing secret configured")
    now = now or datetime.datetime.now(datetime.UTC)
    expires_at = now + datetime.timedelta(seconds=ttl_seconds)
    token = jwt.encode(
        {
            "iss": AI_IDENTITY_TOKEN_ISSUER,
            "sub": agent_id,
            "scope": " ".join(scopes),
            "token_use": "federated",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        },
        secret,
        algorithm=DEFAULT_TOKEN_ALGORITHM,
    )
    return FederatedGrant(agent_id=agent_id, token=token, expires_at=expires_at, scopes=scopes)


def verify_issued_token(token: str, *, secret: str) -> dict[str, Any]:
    """Verify an AI Identity short-lived token we previously issued."""
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[DEFAULT_TOKEN_ALGORITHM],
            issuer=AI_IDENTITY_TOKEN_ISSUER,
            options={"require": ["exp", "iat"], "verify_iss": True},
        )
    except jwt.InvalidTokenError as e:
        raise FederationError(f"issued-token verification failed: {e}") from e


def federate(
    assertion: str,
    issuer: FederatedIssuer,
    *,
    secret: str,
    key_resolver: KeyResolver | None = None,
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    now: datetime.datetime | None = None,
) -> FederatedGrant:
    """End-to-end exchange: verify assertion -> map to agent -> mint token."""
    resolver = key_resolver or default_key_resolver(issuer)
    claims = verify_assertion(assertion, issuer, resolver)
    agent_id = resolve_agent(claims, issuer)
    return issue_token(
        agent_id,
        secret=secret,
        scopes=issuer.default_scopes,
        ttl_seconds=ttl_seconds,
        now=now,
    )
