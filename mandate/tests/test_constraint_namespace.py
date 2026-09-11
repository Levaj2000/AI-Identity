"""Namespaced constraint types, and the signature compatibility they risk.

A mandate could express exactly one bound, `spend_limit`, as a bare field
with no type discriminator. Adding a second kind was not a one-line change,
because there was nothing to dispatch on. Constraints now carry a namespaced
`type`, so types from more than one vocabulary can coexist.

The dangerous half of this change is not the vocabulary, it is that
`constraints` sits inside the signed payload. A field added naively would
give every re-serialized older document a value it was never signed over,
and every signature ever issued would stop verifying. The first test below
is the one that would have caught that.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import ValidationError

from common.config.settings import settings
from mandate.app.constraints import (
    REGISTERED_TYPES,
    TYPE_SPEND_CEILING,
    Constraint,
    is_namespaced,
    unevaluable,
)
from mandate.app.schemas import (
    MandateDocument,
    MandateIssuer,
    MandateStatus,
    MandateSubject,
    SpendLimit,
)
from mandate.app.signing import _build_signable_payload, sign_mandate, verify_signature
from mandate.app.spend import DENY_CONSTRAINT_UNEVALUABLE, evaluate_spend


@pytest.fixture
def fresh_local_key(monkeypatch):
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(settings, "forensic_signing_key_pem", pem, raising=False)
    monkeypatch.setattr(settings, "forensic_signing_key_id", "", raising=False)
    return pem


def _doc(**overrides) -> MandateDocument:
    now = datetime.now(UTC)
    base = {
        "mandate_id": "mnd_deadbeef",
        "status": MandateStatus.active,
        "issuer": MandateIssuer(org_id="org_test", user_id="user_test"),
        "subject": MandateSubject(agent_id="agt_test", org_id="org_test"),
        "scope": ["read:audit"],
        "spend_limit": SpendLimit(limit_cents=10_000),
        "valid_from": now,
        "valid_until": now + timedelta(days=1),
        "signatures": [],
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return MandateDocument(**base)


# --- signature compatibility across the version bump ---


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_older_documents_keep_their_signable_bytes(version):
    """The regression this change could have caused, pinned.

    `constraints` postdates both versions. A document at either must
    canonicalize exactly as it did before the field existed, or every
    signature ever issued at that version breaks.
    """
    payload = _build_signable_payload(_doc(schema_version=version))
    assert b"constraints" not in payload


def test_current_version_does_sign_over_constraints():
    """The other direction: a 1.2 grant's bounds must be covered.

    Without this the namespace would be decorative, since an attacker could
    add or drop a constraint without disturbing the signature.
    """
    payload = _build_signable_payload(_doc(schema_version="1.2"))
    assert b"constraints" in payload


def test_older_signature_still_verifies_after_the_field_was_added(fresh_local_key):
    """End to end, not just the bytes: sign as 1.1, verify as 1.1."""
    mandate = _doc(schema_version="1.1")
    mandate.signatures = [asyncio.run(sign_mandate(mandate))]
    assert asyncio.run(verify_signature(mandate, mandate.signatures[0])) is True


def test_constraints_are_covered_by_the_signature(fresh_local_key):
    """Adding a constraint after signing must break verification.

    Built with `model_construct` to skip validation, which is the faithful
    shape of the attack: someone editing the stored document does not go
    through our validator. It also means the signature, not the parser, is
    what has to catch this.
    """
    mandate = _doc(schema_version="1.2")
    mandate.signatures = [asyncio.run(sign_mandate(mandate))]
    tampered = mandate.model_copy(
        update={"constraints": [Constraint.model_construct(type="test.reserved", params={})]}
    )
    assert asyncio.run(verify_signature(tampered, mandate.signatures[0])) is not True


# --- the namespace itself ---


def test_namespace_requires_two_segments():
    """A bare noun is not a namespace: `ceiling` from two vocabularies
    collides, `spend.ceiling` and `budget.ceiling` do not."""
    assert is_namespaced("spend.ceiling") is True
    assert is_namespaced("mastercard.payment.budget") is True
    assert is_namespaced("ceiling") is False
    assert is_namespaced("Spend.Ceiling") is False
    assert is_namespaced("spend..ceiling") is False


def test_unknown_type_is_rejected_not_skipped():
    """The whole point. A bound this version cannot read may be the one
    restricting the grant, so it must not parse into silence."""
    with pytest.raises(ValidationError) as exc:
        Constraint(type="someone.else.budget", params={"max": 5})
    assert "someone.else.budget" in str(exc.value)


def test_malformed_type_is_rejected():
    with pytest.raises(ValidationError):
        Constraint(type="not_namespaced", params={})


def test_spend_ceiling_is_registered_but_not_allowed_inline():
    """The vocabulary names the bound the document already enforces, while
    `spend_limit` stays its only encoding. Two ways to say one thing is how
    the two end up disagreeing."""
    assert TYPE_SPEND_CEILING in REGISTERED_TYPES
    with pytest.raises(ValidationError) as exc:
        Constraint(type=TYPE_SPEND_CEILING, params={"limit_cents": 500})
    assert "own field" in str(exc.value)


def test_mandate_rejects_an_unknown_constraint_at_parse():
    with pytest.raises(ValidationError):
        _doc(constraints=[{"type": "unregistered.thing", "params": {}}])


def test_mandate_without_constraints_is_unchanged():
    doc = _doc()
    assert doc.constraints == []
    assert doc.schema_version == "1.2"


# --- registered but not yet evaluable ---


def test_unevaluable_reports_registered_types_with_no_evaluator():
    """A type can be named before it can be checked. The document should
    still parse so an operator can see what the grant holds."""
    assert unevaluable([]) == []


def test_spending_denies_on_a_bound_nobody_evaluated(monkeypatch):
    """Naming a type is a promise to evaluate it. Until that promise is
    kept, spending against the grant would assert a bound was satisfied
    when nothing checked it.
    """
    import mandate.app.constraints as c

    monkeypatch.setattr(c, "REGISTERED_TYPES", frozenset({"test.reserved"}))
    monkeypatch.setattr(c, "_FIELD_BACKED_TYPES", frozenset())
    monkeypatch.setattr(c, "EVALUABLE_TYPES", frozenset())

    outcome = evaluate_spend(
        status=MandateStatus.active,
        spend_limit=SpendLimit(limit_cents=10_000),
        spent_cents=0,
        amount_cents=100,
        currency="USD",
        settlement=False,
        constraints=[Constraint.model_construct(type="test.reserved", params={})],
    )
    assert outcome.accepted is False
    assert outcome.deny_reason == DENY_CONSTRAINT_UNEVALUABLE
    assert outcome.new_spent_cents == 0
