"""Unit tests for the EU AI Act Annex III risk-class validator."""

import pytest

from common.validation.eu_ai_act import (
    ALLOWED_RISK_CLASSES,
    ANNEX_III_CATEGORIES,
    NOT_IN_SCOPE,
    validate_risk_class,
)


def test_none_is_valid():
    """None means 'not classified yet' — always accepted."""
    assert validate_risk_class(None) is None


def test_not_in_scope_sentinel_is_valid():
    """'not_in_scope' is the explicit 'evaluated, not Annex III' marker."""
    assert validate_risk_class(NOT_IN_SCOPE) == "not_in_scope"


@pytest.mark.parametrize("code", sorted(ANNEX_III_CATEGORIES.keys()))
def test_all_annex_iii_codes_accepted(code: str):
    """Every canonical Annex III code passes validation."""
    assert validate_risk_class(code) == code


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "high-risk",
        "ANNEX_III_3A",
        "9(a)",  # category 9 doesn't exist
        "3(z)",  # letter not in that category is still rejected — strict allowlist
        "3",  # missing letter suffix
        "(a)",  # missing number
        "3(A)",  # uppercase letter not canonical
        " 3(a)",  # leading whitespace
        "3(a) ",  # trailing whitespace
        "not in scope",  # wrong separator
    ],
)
def test_invalid_values_raise(bad: str):
    """Anything not in the allowlist is rejected with a helpful message."""
    with pytest.raises(ValueError, match="Invalid eu_ai_act_risk_class"):
        validate_risk_class(bad)


def test_allowed_set_shape():
    """The allowed set is the union of Annex III codes + the sentinel — no extras, no gaps."""
    assert frozenset({*ANNEX_III_CATEGORIES.keys(), NOT_IN_SCOPE}) == ALLOWED_RISK_CLASSES
    assert NOT_IN_SCOPE in ALLOWED_RISK_CLASSES
    # Spot-check representative codes from each category family.
    for code in ("1(a)", "2(a)", "3(a)", "4(b)", "5(b)", "6(d)", "7(c)", "8(b)"):
        assert code in ALLOWED_RISK_CLASSES
