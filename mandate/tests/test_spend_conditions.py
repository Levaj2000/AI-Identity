"""Mandate conditions are evaluated before a spend is recorded.

`conditions` is part of the signed grant. Until now nothing evaluated it,
anywhere: /verify reported valid while ignoring it (fixed in #531) and the
gateway's enforcement path never saw it at all.

The evaluation lands in the Mandate Service rather than the gateway for one
reason, and it is worth stating because the opposite arrangement looks
natural: the check has to be atomic with the spend. Evaluating at the
gateway means evaluating after the draw response comes back, by which point
an accepted spend has already been recorded against the budget of a request
about to be denied. So the gateway sends the context it alone holds, and the
service that owns the grant applies its own terms before mutating state.

Conditions reuse `common.policy.eval.evaluate_when`, the same function that
evaluates a policy `when` clause, so both mean the same thing and fail the
same way.
"""

from mandate.app.schemas import MandateStatus, SpendLimit
from mandate.app.spend import (
    DENY_CONDITIONS_UNMET,
    DENY_LIMIT_EXCEEDED,
    DENY_MANDATE_INACTIVE,
    evaluate_spend,
)

LIMIT = SpendLimit(limit_cents=10_000, currency="USD")


def _spend(**overrides):
    kwargs = {
        "status": MandateStatus.active,
        "spend_limit": LIMIT,
        "spent_cents": 0,
        "amount_cents": 1_000,
        "currency": "USD",
        "settlement": False,
    }
    kwargs.update(overrides)
    return evaluate_spend(**kwargs)


def test_no_conditions_is_unchanged():
    """The common case must not move: no conditions, no new denial."""
    out = _spend()
    assert out.accepted is True
    assert out.deny_reason is None
    assert out.condition_results == []


def test_satisfied_condition_allows():
    out = _spend(conditions={"env": "prod"}, context={"env": "prod"})
    assert out.accepted is True
    assert out.deny_reason is None
    assert len(out.condition_results) == 1
    assert out.condition_results[0]["match"] is True


def test_unsatisfied_condition_denies_and_records_nothing():
    out = _spend(conditions={"env": "prod"}, context={"env": "staging"})
    assert out.accepted is False
    assert out.deny_reason == DENY_CONDITIONS_UNMET
    assert out.new_spent_cents == 0  # budget intact, nothing consumed
    assert out.condition_results[0]["expected"] == "prod"
    assert out.condition_results[0]["actual"] == "staging"


def test_missing_context_key_denies():
    """A condition whose key is absent cannot be shown to hold.

    This is the case that matters for rollout: a caller that has not been
    updated to send context gets denied on a conditioned mandate rather than
    quietly spending against one.
    """
    out = _spend(conditions={"env": "prod"}, context={})
    assert out.accepted is False
    assert out.deny_reason == DENY_CONDITIONS_UNMET
    assert out.condition_results[0]["match"] is False


def test_conditions_checked_before_the_limit():
    """An inapplicable grant is not a budget question.

    Over the limit AND failing a condition reports the condition, because
    asking how much budget is left on a grant that does not cover the request
    is the wrong question.
    """
    out = _spend(
        amount_cents=99_999,
        conditions={"env": "prod"},
        context={"env": "staging"},
    )
    assert out.deny_reason == DENY_CONDITIONS_UNMET


def test_status_still_outranks_conditions():
    """A revoked grant is revoked whatever its conditions say."""
    out = _spend(
        status=MandateStatus.revoked,
        conditions={"env": "prod"},
        context={"env": "prod"},
    )
    assert out.deny_reason == DENY_MANDATE_INACTIVE


def test_satisfied_conditions_do_not_rescue_an_over_limit_spend():
    """Guard the other direction: conditions holding is not a bypass."""
    out = _spend(
        amount_cents=99_999,
        conditions={"env": "prod"},
        context={"env": "prod"},
    )
    assert out.accepted is False
    assert out.deny_reason == DENY_LIMIT_EXCEEDED
    # The passing conditions still ride along, so the audit row shows the
    # grant did cover the request and the budget is what refused it.
    assert out.condition_results[0]["match"] is True


def test_multi_condition_reports_only_the_failing_field():
    out = _spend(
        conditions={"env": "prod", "tier": "gold"},
        context={"env": "prod", "tier": "bronze"},
    )
    assert out.deny_reason == DENY_CONDITIONS_UNMET
    failed = [r["field"] for r in out.condition_results if not r["match"]]
    assert failed == ["tier"]


def test_settlement_path_also_respects_conditions():
    """A judgment call, stated rather than buried.

    Settlement exists because money that already moved cannot be un-moved,
    which is why an over-limit settlement IS recorded and flips the mandate
    to `exceeded`. The same reasoning could argue a condition-failing
    settlement should be recorded too.

    It is not, because incrementing `spent_cents` asserts that this mandate's
    budget funded the spend, and a failed condition says this grant did not
    cover the request at all. Recording it would put money against a grant
    that did not authorize it.

    Nothing is lost by refusing: the route writes the audit row and the event
    log entry on every call, accepted or not, so the attempt and its reason
    are still in the chain. Only the budget counter stays untouched.
    """
    out = _spend(
        settlement=True,
        amount_cents=99_999,
        conditions={"env": "prod"},
        context={"env": "staging"},
    )
    assert out.accepted is False
    assert out.deny_reason == DENY_CONDITIONS_UNMET
    assert out.new_spent_cents == 0
