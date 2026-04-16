"""Lock in that every sample under docs/policies/samples/ passes the
PolicyValidator and evaluates the way its header comments promise.

If a future validator change rejects a sample, or an evaluator change
flips its behavior, this test catches it before the docs go stale.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest
import yaml

from common.policy.eval import evaluate_policy
from common.validation.policy import PolicyValidator

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "docs" / "policies" / "samples"


def _load(name: str) -> dict:
    with (SAMPLES_DIR / name).open() as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize("path", sorted(glob.glob(str(SAMPLES_DIR / "*.yaml"))))
def test_sample_passes_validator(path: str) -> None:
    with open(path) as f:
        rules = yaml.safe_load(f)
    result = PolicyValidator().validate(rules)
    assert result.valid, [f"{e.field}: {e.message}" for e in result.errors]


def test_team_scoped_payments_allows_and_denies() -> None:
    rules = _load("03-team-scoped-payments.yaml")
    allowed = evaluate_policy(rules, {"team": "payments"}, "/v1/payments/authorize", "POST")
    denied = evaluate_policy(rules, {"team": "sales"}, "/v1/payments/authorize", "POST")
    assert allowed.allowed
    assert not denied.allowed
    assert "not_in" in (denied.deny_reason or "")


def test_prod_payments_combined_denies_staging() -> None:
    rules = _load("05-prod-payments-combined.yaml")
    denied = evaluate_policy(
        rules,
        {"environment": "staging", "team": "payments"},
        "/v1/payments/authorize",
        "POST",
    )
    assert not denied.allowed
    assert "environment" in (denied.deny_reason or "")


def test_compliance_deny_list_beats_allow_list() -> None:
    rules = _load("06-compliance-deny-admin.yaml")
    denied = evaluate_policy(rules, {}, "/v1/admin/rotate-keys", "GET")
    assert not denied.allowed
    assert (denied.deny_reason or "").startswith("denied_endpoints:")


def test_full_stack_branches() -> None:
    rules = _load("08-full-stack-prod-write.yaml")
    md = {"environment": "production", "team": "payments", "framework": "langchain"}
    assert evaluate_policy(rules, md, "/v1/payments/authorize", "POST").allowed
    get_denied = evaluate_policy(rules, md, "/v1/payments/authorize", "GET")
    assert not get_denied.allowed
    assert "allowed_methods" in (get_denied.deny_reason or "")
    admin_denied = evaluate_policy(rules, md, "/v1/payments/admin/rotate-key", "POST")
    assert not admin_denied.allowed
    assert "denied_endpoints" in (admin_denied.deny_reason or "")
