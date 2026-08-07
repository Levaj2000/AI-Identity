"""Mint / attenuate / verify Biscuit presentation credentials for mandates.

A Biscuit here is a PRESENTATION credential, not the mandate itself: the
authoritative grant stays the ECDSA-signed MandateDocument in MongoDB, and
cumulative spend state stays in MongoDB. The Biscuit wraps the grant's terms
as Datalog facts + checks so an agent can present (and offline-attenuate)
its authority at the gateway, which then settles the actual draw against the
Mandate Service.

Datalog vocabulary — token side (minted from the grant). CRITICAL naming
rule: informational facts must NEVER share a name with a fact the checks
query (subject/amount/scope/currency/time), or the token's own facts would
satisfy its own checks and the verifier's presented values would be
ignored. Verifier-queried names appear in the token ONLY inside checks.
    mandate("mnd_ab12cd34");            # links back to the signed document
    subject_agent("<platform agent UUID>");   # informational
    org("<subject org id>");
    limit_cents(10000);                 # informational
    granted_currency("USD");            # informational
    scope_granted("spend:commerce");    # one fact per granted scope
    check if subject($s), $s == "<agent uuid>";
    check if scope($s), scope_granted($s);
    check if amount($a), $a <= 10000;          # only when the grant has a spend limit
    check if currency($c), $c == "USD";        # only when the grant has a spend limit
    check if time($t), $t >= <valid_from>;
    check if time($t), $t < <valid_until>;     # only when the grant expires

Verifier side (the gateway at settlement) supplies the request as facts:
    subject(<presented agent id>); amount(<cents>); scope(<action scope>);
    currency(<cur>); time(<now>);
and the policy `allow if mandate($id)`. Every token check must pass.

Attenuation appends `check if amount($a), $a <= <narrower>` blocks — a
parent agent can hand a sub-agent a tighter ceiling with no callback to us.

Honesty note (demo tier): a Biscuit is a bearer token. The subject check
binds the token to a claimed agent identity, but it is the gateway that
asserts which identity was presented — real possession-binding requires the
gateway to authenticate the agent independently (Phase 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt

from biscuit_auth import (
    Algorithm,
    AuthorizerBuilder,
    Biscuit,
    BiscuitBuilder,
    BlockBuilder,
    KeyPair,
    PrivateKey,
    PublicKey,
)


class BiscuitUnavailableError(RuntimeError):
    """Raised when minting is requested but no root key is configured."""


@dataclass(frozen=True)
class MintedBiscuit:
    token: str  # URL-safe base64
    root_public_key: str  # hex, 32 bytes Ed25519
    revocation_ids: list[str]


@dataclass(frozen=True)
class PresentationResult:
    allowed: bool
    mandate_id: str | None
    block_count: int
    revocation_ids: list[str] = field(default_factory=list)
    deny_detail: str | None = None  # biscuit's own error, names the failing check/block


def _keypair_from_pem(private_key_pem: str) -> KeyPair:
    if not private_key_pem.strip():
        raise BiscuitUnavailableError("no Biscuit root key configured (BISCUIT_ROOT_KEY_PEM)")
    return KeyPair.from_private_key(PrivateKey.from_pem(private_key_pem))


def root_public_key_hex(private_key_pem: str) -> str:
    """Derive the hex-encoded Ed25519 public key from the configured PEM."""
    return bytes(_keypair_from_pem(private_key_pem).public_key.to_bytes()).hex()


def _public_key(hex_key: str) -> PublicKey:
    return PublicKey.from_bytes(bytes.fromhex(hex_key), Algorithm.Ed25519)


def _revocation_ids(token: Biscuit) -> list[str]:
    rev = token.revocation_ids
    return list(rev() if callable(rev) else rev)


def mint_mandate_biscuit(
    *,
    private_key_pem: str,
    mandate_id: str,
    subject_agent_id: str,
    subject_org_id: str,
    scope: list[str],
    valid_from: dt.datetime,
    valid_until: dt.datetime | None = None,
    limit_cents: int | None = None,
    currency: str = "USD",
) -> MintedBiscuit:
    """Mint the authority block from a mandate's grant terms.

    Only grant fields go in — never runtime state (spent_cents lives in
    MongoDB and would be stale the moment the token left the building).
    """
    keypair = _keypair_from_pem(private_key_pem)
    builder = BiscuitBuilder()
    builder.add_code(
        """
        mandate({mandate_id});
        subject_agent({agent_id});
        org({org_id});
        check if subject($s), $s == {agent_id};
        check if scope($s), scope_granted($s);
        check if time($t), $t >= {valid_from};
        """,
        {
            "mandate_id": mandate_id,
            "agent_id": subject_agent_id,
            "org_id": subject_org_id,
            "valid_from": valid_from,
        },
    )
    for s in scope:
        builder.add_code("scope_granted({s});", {"s": s})
    if valid_until is not None:
        builder.add_code("check if time($t), $t < {valid_until};", {"valid_until": valid_until})
    if limit_cents is not None:
        # The ceiling check admits settlement mode: money that already moved
        # must be RECORDABLE past the grant (that's how a breach gets flipped
        # to `exceeded` and evidenced) — so the authority ceiling yields to a
        # settlement(true) fact. Only the verifier (the gateway) asserts that
        # fact; a token holder cannot, because holder-added facts are scoped
        # to their own block and invisible to this check. Attenuation
        # ceilings (attenuate_spend_ceiling) stay absolute on purpose: a
        # sub-agent's cap is a hard delegation bound, not a grant.
        builder.add_code(
            """
            limit_cents({limit});
            granted_currency({currency});
            check if amount($a), $a <= {limit} or settlement(true);
            check if currency($c), $c == {currency};
            """,
            {"limit": limit_cents, "currency": currency},
        )

    token = builder.build(keypair.private_key)
    return MintedBiscuit(
        token=token.to_base64(),
        root_public_key=bytes(keypair.public_key.to_bytes()).hex(),
        revocation_ids=_revocation_ids(token),
    )


def attenuate_spend_ceiling(
    token_b64: str,
    root_public_key: str,
    *,
    ceiling_cents: int,
) -> str:
    """Append a narrower spend ceiling — the offline delegation move.

    Anyone holding the token can do this without contacting the issuer;
    rights only ever shrink (the authority ceiling still applies too).
    """
    token = Biscuit.from_base64(token_b64, _public_key(root_public_key))
    block = BlockBuilder()
    block.add_code("check if amount($a), $a <= {ceiling};", {"ceiling": ceiling_cents})
    return token.append(block).to_base64()


def authorize_presentation(
    token_b64: str,
    root_public_key: str,
    *,
    agent_id: str,
    amount_cents: int,
    scope: str,
    currency: str = "USD",
    settlement: bool = False,
    now: dt.datetime | None = None,
) -> PresentationResult:
    """The gateway side: verify signatures, then run every token check
    against the presented request facts.

    Signature/parse failures and check failures both come back as
    ``allowed=False`` with the library's own error text in ``deny_detail``
    (it names the failing check and block — audit-friendly).
    """
    try:
        token = Biscuit.from_base64(token_b64, _public_key(root_public_key))
    except Exception as e:  # invalid signature, tampered bytes, wrong root key
        return PresentationResult(
            allowed=False,
            mandate_id=None,
            block_count=0,
            deny_detail=f"{type(e).__name__}: {e}",
        )

    mandate_id = _extract_mandate_id(token)

    builder = AuthorizerBuilder()
    builder.add_code(
        """
        subject({agent_id});
        amount({amount});
        scope({scope});
        currency({currency});
        allow if mandate($id);
        """,
        {"agent_id": agent_id, "amount": amount_cents, "scope": scope, "currency": currency},
    )
    if settlement:
        # Verifier-asserted: lets the authority ceiling yield in settlement
        # mode (see mint). Attenuation-block ceilings do not reference it.
        builder.add_code("settlement(true);")
    if now is not None:
        builder.add_code("time({now});", {"now": now})
    else:
        builder.set_time()

    try:
        builder.build(token).authorize()
    except Exception as e:  # AuthorizationError — names the failing check
        return PresentationResult(
            allowed=False,
            mandate_id=mandate_id,
            block_count=token.block_count(),
            revocation_ids=_revocation_ids(token),
            deny_detail=str(e),
        )

    return PresentationResult(
        allowed=True,
        mandate_id=mandate_id,
        block_count=token.block_count(),
        revocation_ids=_revocation_ids(token),
    )


def _extract_mandate_id(token: Biscuit) -> str | None:
    """Read the mandate id from the authority block's Datalog source.

    Parsed from block 0 only — attenuation blocks cannot spoof it.
    """
    source = token.block_source(0)
    for line in source.splitlines():
        line = line.strip()
        if line.startswith('mandate("') and line.endswith('");'):
            return line[len('mandate("') : -len('");')]
    return None
