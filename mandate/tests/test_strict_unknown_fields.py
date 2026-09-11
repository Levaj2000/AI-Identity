"""Strict handling of grant content this version cannot evaluate.

A mandate is an authorization document. Two ways it can carry a restriction
the service does not understand, and both used to resolve as "more authority",
which is the wrong direction for an authorization decision to fail in:

  1. An unrecognized top-level field, silently dropped by Pydantic's default
     ``extra="ignore"``.
  2. A populated ``conditions`` map, which is inside the signed grant and which
     nothing in this service evaluates.

These tests pin both to fail closed. They are written sync + ``asyncio.run``
for the same reason as ``test_signing.py``: no pytest-asyncio dependency.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import ValidationError

from common.config.settings import settings
from mandate.app.routers.verify import verify_mandate
from mandate.app.schemas import (
    IssueMandateRequest,
    MandateDocument,
    MandateIssuer,
    MandateResponse,
    MandateStatus,
    MandateSubject,
    VerifyMandateRequest,
)
from mandate.app.signing import sign_mandate


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


def _mandate_kwargs(**overrides):
    now = datetime.now(UTC)
    base = {
        "mandate_id": "mnd_deadbeef",
        "status": MandateStatus.active,
        "issuer": MandateIssuer(org_id="org_test", user_id="user_test"),
        "subject": MandateSubject(agent_id="agt_test", org_id="org_test"),
        "scope": ["read:audit"],
        "valid_from": now,
        "valid_until": now + timedelta(days=1),
        "signatures": [],
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


def _signed(mandate: MandateDocument) -> MandateDocument:
    mandate.signatures = [asyncio.run(sign_mandate(mandate))]
    return mandate


def _verify(mandate: MandateDocument, **body_kwargs):
    request = VerifyMandateRequest(mandate=MandateResponse(**mandate.model_dump()), **body_kwargs)
    return asyncio.run(verify_mandate(request, required_scope=None))


# --- 1. Unrecognized top-level fields ---


def test_unknown_field_is_rejected_not_dropped():
    """A field this version does not know is a parse error.

    Under ``extra="ignore"`` this constructed fine and lost the field, so a
    mandate issued at a newer schema version verified against a narrower
    reading of its own grant.
    """
    with pytest.raises(ValidationError) as exc:
        MandateDocument(**_mandate_kwargs(geo_restriction={"allow": ["US"]}))
    assert "geo_restriction" in str(exc.value)


def test_unknown_field_on_issue_request_is_rejected():
    """Same rule one step earlier, so a misspelled limit is not a wide grant."""
    with pytest.raises(ValidationError) as exc:
        IssueMandateRequest(
            subject_agent_id="agt_test",
            subject_org_id="org_test",
            scope=["read:audit"],
            spend_limmit={"limit_cents": 5000},  # codespell:ignore
        )
    assert "spend_limmit" in str(exc.value)  # codespell:ignore


def test_known_fields_still_construct():
    """Guard against the rule being too broad to issue an ordinary mandate."""
    m = MandateDocument(**_mandate_kwargs(conditions={"env": "prod"}))
    assert m.conditions == {"env": "prod"}


# --- 2. Conditions nothing evaluates ---


def test_mandate_without_conditions_verifies(fresh_local_key):
    m = _signed(MandateDocument(**_mandate_kwargs()))
    result = _verify(m)
    assert result.checks["conditions_evaluable"] is True
    assert result.valid is True


def test_unevaluated_conditions_fail_closed(fresh_local_key):
    """The bug this file exists for.

    An issuer signs {"env": "staging"}. Nothing here evaluates it. Before this
    change the endpoint answered ``valid: true`` in production, and a caller
    could not tell that verdict apart from one over a mandate with no
    conditions at all.
    """
    m = _signed(MandateDocument(**_mandate_kwargs(conditions={"env": "staging"})))
    result = _verify(m)

    assert result.checks["conditions_evaluable"] is False
    assert result.valid is False
    assert "env" in result.error
    # Every other check still passes: the mandate is well-formed and correctly
    # signed. It is the unevaluated restriction alone that sinks the verdict.
    assert result.checks["signatures_valid"] is True
    assert result.checks["status_active"] is True
    assert result.checks["not_expired"] is True


def test_caller_can_assert_it_evaluated_conditions(fresh_local_key):
    """The escape is an assertion of work done, not a bypass of the check."""
    m = _signed(MandateDocument(**_mandate_kwargs(conditions={"env": "staging"})))
    result = _verify(m, conditions_evaluated=True)
    assert result.checks["conditions_evaluable"] is True
    assert result.valid is True


def test_conditions_stay_inside_the_signature(fresh_local_key):
    """Conditions are part of the grant, so editing them breaks the signature.

    Without this, failing closed on conditions would be theatre: an attacker
    would strip the field and get a clean verdict.
    """
    m = _signed(MandateDocument(**_mandate_kwargs(conditions={"env": "staging"})))
    stripped = m.model_copy(update={"conditions": {}})

    result = _verify(stripped)
    assert result.checks["signatures_valid"] is False
    assert result.valid is False
