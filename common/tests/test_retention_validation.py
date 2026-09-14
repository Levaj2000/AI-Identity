"""Unit tests for the retention policy validator (v0.5.0, phase 2).

Pins the decision semantics: duration parsing, shadow detection direction,
overlap, catch-all enforcement, and tier/shortening rules. These run without
the API app (fast); the HTTP surface is covered in api/tests/.
"""

from datetime import UTC, datetime, timedelta

import pytest

from common.schemas.retention import RetentionPolicyCreate
from common.validation.retention import (
    RetentionPolicyValidator,
    parse_duration,
    selector_matches,
)


def _body(rules, **kwargs):
    payload = {
        "rules": rules,
        "default_rule": {"retain_for": "P90D"},
    }
    payload.update(kwargs)
    return RetentionPolicyCreate(**payload)


def _rule(rule_id, selector, retain_for="P90D", **kwargs):
    rule = {"rule_id": rule_id, "selector": selector, "retain_for": retain_for}
    rule.update(kwargs)
    return rule


def _catchall(retain_for="P90D"):
    return _rule("r_catchall", {}, retain_for)


# ── parse_duration ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("P30D", 30.0),
        ("P13W", 91.0),
        ("P1Y", 365.0),
        ("P1Y2W3D", 365 + 14 + 3.0),
        ("indefinite", float("inf")),
        ("INDEFINITE", float("inf")),
    ],
)
def test_parse_duration_valid(text, expected):
    days, err = parse_duration(text)
    assert err is None
    assert days == expected


@pytest.mark.parametrize("text", ["P1M", "P6M", "PT1H", "30 days", "", "P", "yesterday"])
def test_parse_duration_rejects_months_and_garbage(text):
    _, err = parse_duration(text)
    assert err is not None
    if "M" in text and text.startswith("P"):
        assert "month" in err.lower()


# ── selector_matches ───────────────────────────────────────────────────


def test_selector_matches():
    assert selector_matches({"decision": ["deny"]}, {"decision": "deny"})
    assert selector_matches({"decision": "deny"}, {"decision": "deny"})
    assert not selector_matches({"decision": ["deny"]}, {"decision": "allow"})
    assert not selector_matches({"decision": ["deny"]}, {"flow_tag": "prod"})  # missing key
    assert selector_matches({}, {"decision": "deny"})  # catch-all matches all


# ── catch-all / shadowing ──────────────────────────────────────────────


def test_missing_catch_all_is_error():
    body = _body([_rule("r1", {"decision": ["deny"]})])
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("catch-all" in e for e in errors)


def test_catch_all_mid_policy_is_error():
    body = _body([_catchall(), _rule("r1", {"decision": ["deny"]})])
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("unreachable" in e for e in errors)


def test_broader_earlier_rule_shadows_narrower_later():
    # r_broad matches every record r_narrow could match -> r_narrow unreachable.
    body = _body(
        [
            _rule("r_broad", {"decision": ["deny", "allow"]}, "P60D"),
            _rule("r_narrow", {"decision": ["deny"]}, "P60D"),
            _catchall("P60D"),
        ]
    )
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("shadowed" in e and "r_narrow" in e for e in errors)


def test_narrower_earlier_rule_does_not_shadow_broader_later():
    # allow-records reach r_wide; it is not shadowed.
    body = _body(
        [
            _rule("r_narrow", {"decision": ["deny"]}, "P60D"),
            _rule("r_wide", {"decision": ["deny", "allow"]}, "P60D"),
            _catchall("P60D"),
        ]
    )
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert not any("shadowed" in e for e in errors)


def test_refined_later_rule_is_shadowed():
    # Every prod deny already matches r1 -> r2 can never fire.
    body = _body(
        [
            _rule("r1", {"decision": ["deny"]}, "P60D"),
            _rule("r2", {"decision": ["deny"], "flow_tag": ["prod"]}, "P60D"),
            _catchall("P60D"),
        ]
    )
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("shadowed" in e and "r2" in e for e in errors)


def test_overlapping_rules_warn_without_shadowing():
    body = _body(
        [
            _rule("r1", {"decision": ["deny"]}, "P60D"),
            _rule("r2", {"flow_tag": ["prod"]}, "P60D"),
            _catchall("P60D"),
        ]
    )
    errors, warnings = RetentionPolicyValidator("business").validate(body)
    assert errors == []
    assert any("r1" in w and "r2" in w for w in warnings)


def test_no_warning_for_rule_before_catch_all():
    body = _body([_rule("r_deny", {"decision": ["deny"]}), _catchall()])
    errors, warnings = RetentionPolicyValidator("business").validate(body)
    assert errors == []
    assert warnings == []


def test_unknown_selector_key_rejected():
    body = _body([_rule("r1", {"frobnicate": ["x"]}), _catchall()])
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("unknown selector key" in e for e in errors)


def test_duplicate_rule_ids_rejected():
    body = _body([_rule("r1", {"decision": ["deny"]}), _rule("r1", {}, "P60D")])
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("duplicate rule_id" in e for e in errors)


# ── tiers / durations ──────────────────────────────────────────────────


def test_free_tier_rejects_custom_policy():
    body = _body([_rule("r1", {"decision": ["deny"]}), _catchall()])
    errors, _ = RetentionPolicyValidator("free").validate(body)
    assert errors, "free tier must reject custom policies"


def test_redact_after_must_be_strictly_less():
    body = _body(
        [
            _rule("r1", {"decision": ["deny"]}, "P90D", redact_after="P90D"),
            _catchall(),
        ]
    )
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("redact_after" in e for e in errors)

    body = _body(
        [
            _rule("r1", {"decision": ["deny"]}, "P90D", redact_after="P89D"),
            _catchall(),
        ]
    )
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert errors == []


def test_wrong_sampling_alg_rejected():
    body = _body(
        [
            _rule(
                "r1",
                {"decision": ["deny"]},
                "P90D",
                sampling={"alg": "md5-mod-v1", "of": 100, "keep": 10},
            ),
            _catchall(),
        ]
    )
    errors, _ = RetentionPolicyValidator("business").validate(body)
    assert any("sha256-mod-v1" in e for e in errors)


# ── shortening ─────────────────────────────────────────────────────────


class _FakePolicy:
    def __init__(self, rules):
        self.rules = rules


def test_shortening_sets_default_effective_at():
    current = _FakePolicy(
        [_rule("r1", {"decision": ["deny"]}, "P90D"), _rule("r_catchall", {}, "P90D")]
    )
    now = datetime.now(UTC)
    body = _body(
        [_rule("r1", {"decision": ["deny"]}, "P60D"), _rule("r_catchall", {}, "P60D")],
        approvals=[
            {"by": "a", "at": now.isoformat()},
            {"by": "b", "at": now.isoformat()},
        ],
    )
    validator = RetentionPolicyValidator("business", current_policy=current, now=now)
    errors, _ = validator.validate(body)
    assert errors == []
    assert body.effective_at is not None
    assert body.effective_at >= now + timedelta(days=7) - timedelta(seconds=5)


def test_shortening_without_dual_approval_fails():
    current = _FakePolicy(
        [_rule("r1", {"decision": ["deny"]}, "P90D"), _rule("r_catchall", {}, "P90D")]
    )
    body = _body(
        [_rule("r1", {"decision": ["deny"]}, "P60D"), _rule("r_catchall", {}, "P60D")],
        approvals=[{"by": "a", "at": datetime.now(UTC).isoformat()}],
    )
    errors, _ = RetentionPolicyValidator("business", current_policy=current).validate(body)
    assert any("dual approval" in e for e in errors)


def test_lengthening_needs_no_approval():
    current = _FakePolicy(
        [_rule("r1", {"decision": ["deny"]}, "P60D"), _rule("r_catchall", {}, "P60D")]
    )
    body = _body([_rule("r1", {"decision": ["deny"]}, "P90D"), _rule("r_catchall", {}, "P90D")])
    errors, _ = RetentionPolicyValidator("business", current_policy=current).validate(body)
    assert errors == []
    assert body.effective_at is None  # no forced delay when not shortening
