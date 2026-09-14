"""RetentionPolicyValidator — create-time validation for retention policies (v0.5.0).

Fail-closed: any error rejects the policy version. Warnings (e.g.
broad-before-narrow) are returned alongside and surfaced in the response
without blocking creation.

Decisions enforced here come from the design doc
(Notion "Forensic Retention Policies — Policy Model (v0.5.0)"):

* first-match precedence with a required terminal catch-all, shadowed-rule
  rejection, and broad-before-narrow warnings;
* ISO-8601 durations restricted to days/weeks/years (``P1M`` is ambiguous
  and rejected); ``redact_after`` strictly less than ``retain_for``;
* sampling pinned to ``sha256-mod-v1`` inside the immutable version;
* tier ceilings (free: no custom policy; pro: P90D; business: P13M;
  enterprise: no ceiling), the regulated P6M minimum, and a platform floor;
* shortening friction: dual approval + 7-day delayed effect.

Also exported: :func:`selector_matches`, the first-match predicate shared
by the explain endpoint.
"""

import logging
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from common.models.retention_policy import SAMPLING_ALG_V1, RetentionPolicy
from common.schemas.retention import RetentionPolicyCreate

logger = logging.getLogger("ai_identity.validation.retention")

# ── Constants ────────────────────────────────────────────────────────────

_DURATION_RE = re.compile(r"^P(?:(\d+)Y)?(?:(\d+)W)?(?:(\d+)D)?$")
_MONTHS_RE = re.compile(r"^P\d+M$")

# Whitelisted selector keys. Anything else is rejected, not ignored.
SELECTOR_KEYS = frozenset(
    {
        "record_class",
        "flow_tag",
        "decision",
        "agent_id",
        "session_id",
        "risk_tier",
        "event_type",
    }
)

# Tier -> maximum retain_for in days. None means no ceiling (indefinite allowed).
TIER_CEILINGS_DAYS: dict[str, float | None] = {
    "pro": 90,
    "business": 395,  # P13M ≈ 13 × 30.4
    "enterprise": None,
}

REGULATED_MIN_DAYS = 180  # flow_tag "regulated" minimum (P6M)
PLATFORM_FLOOR_DAYS = 30  # no rule may retain less than this, any tier
SHORTENING_DELAY = timedelta(days=7)

INFINITE = math.inf


def parse_duration(value: str) -> tuple[float, str | None]:
    """Parse a retention duration string.

    Returns ``(days, error)`` — ``days`` is ``math.inf`` for ``"indefinite"``.
    Only days, weeks, and years are accepted; months (``P1M``) are rejected
    as ambiguous, as is everything else.
    """
    if not isinstance(value, str):
        return 0.0, f"duration must be a string, got {type(value).__name__}"
    text = value.strip()
    if text.lower() == "indefinite":
        return INFINITE, None
    if _MONTHS_RE.match(text):
        return 0.0, (
            f'invalid duration "{value}": months (P1M) are ambiguous — '
            "use days, weeks, or years (e.g. P30D, P13W, P1Y)"
        )
    match = _DURATION_RE.match(text)
    if not match:
        return 0.0, (
            f'invalid duration "{value}": expected ISO-8601 days/weeks/years '
            '(e.g. "P30D", "P13W", "P1Y") or "indefinite"'
        )
    years, weeks, days = match.groups()
    if not any((years, weeks, days)):
        return 0.0, f'invalid duration "{value}": at least one of Y, W, D is required'
    total = (int(years or 0) * 365) + (int(weeks or 0) * 7) + int(days or 0)
    return float(total), None


def _as_set(value: Any) -> set:
    """Normalize a selector value to a set of allowed values.

    Lists become sets; scalars become singletons. Unhashable values (dicts)
    fall back to their repr so comparison never crashes on odd payloads.
    """
    items = value if isinstance(value, list) else [value]
    result = set()
    for item in items:
        try:
            result.add(item)
        except TypeError:
            result.add(repr(item))
    return result


def selector_matches(selector: dict[str, Any], descriptor: dict[str, Any]) -> bool:
    """First-match predicate: does this selector match the record descriptor?

    A selector matches iff for every ``(key, allowed)`` in the selector the
    descriptor carries that key AND the descriptor's value is in the allowed
    set (list) or equals it (scalar). An empty selector matches everything.
    """
    for key, allowed in selector.items():
        if key not in descriptor:
            return False
        value = descriptor[key]
        if isinstance(allowed, list):
            if value not in allowed:
                return False
        elif value != allowed:
            return False
    return True


def _shadows(earlier: dict[str, Any], later: dict[str, Any]) -> bool:
    """True iff `earlier` matches every record `later` could match.

    Rule j is fully shadowed by earlier rule i iff for every key k in
    i.selector, k is also in j.selector and i's allowed set for k is a
    superset of j's: any record matching j carries k with a value in j's
    (smaller) set, hence also in i's (larger) set, so i matches it first.
    An empty earlier selector shadows everything.
    """
    earlier_sel = earlier.get("selector") or {}
    later_sel = later.get("selector") or {}
    for key, allowed in earlier_sel.items():
        if key not in later_sel:
            return False
        if not _as_set(allowed) >= _as_set(later_sel[key]):
            return False
    return True


def _overlaps(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """True iff some record could match both selectors.

    Overlap holds when no key present in both selectors has disjoint allowed
    sets. Selectors sharing no keys always overlap.
    """
    first_sel = first.get("selector") or {}
    second_sel = second.get("selector") or {}
    for key in first_sel:
        if key in second_sel and _as_set(first_sel[key]).isdisjoint(_as_set(second_sel[key])):
            return False
    return True


class RetentionPolicyValidator:
    """Validates a candidate retention policy version.

    ``current_policy`` is the org's active version (None for the first
    version) — used for shortening detection. Returns ``(errors, warnings)``;
    any error rejects the version.
    """

    def __init__(
        self,
        org_tier: str,
        current_policy: RetentionPolicy | None = None,
        now: datetime | None = None,
    ) -> None:
        self.org_tier = org_tier
        self.current_policy = current_policy
        self.now = now or datetime.now(UTC)

    # ── Entry point ──────────────────────────────────────────────────

    def validate(self, body: RetentionPolicyCreate) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        if self.org_tier == "free":
            errors.append(
                "custom retention policies are not available on the free tier "
                "(fixed P30D retention applies)"
            )
            return errors, warnings
        if self.org_tier not in TIER_CEILINGS_DAYS:
            errors.append(f'unknown organization tier "{self.org_tier}"')
            return errors, warnings

        rules = [rule.model_dump() for rule in body.rules]

        self._validate_rule_ids(rules, errors)
        self._validate_rule_shapes(rules, errors)
        self._validate_catch_all(rules, errors)
        self._validate_shadowing(rules, errors)
        self._validate_broad_before_narrow(rules, warnings)
        self._validate_default_rule(body, errors)
        self._validate_shortening(body, rules, errors)

        return errors, warnings

    # ── Structural checks ────────────────────────────────────────────

    def _validate_rule_ids(self, rules: list[dict], errors: list[str]) -> None:
        seen: set[str] = set()
        for rule in rules:
            rule_id = rule.get("rule_id")
            if rule_id in seen:
                errors.append(f'duplicate rule_id "{rule_id}"')
            seen.add(rule_id)

    def _validate_rule_shapes(self, rules: list[dict], errors: list[str]) -> None:
        ceiling = TIER_CEILINGS_DAYS[self.org_tier]
        for rule in rules:
            rule_id = rule.get("rule_id", "?")
            selector = rule.get("selector") or {}
            for key in selector:
                if key not in SELECTOR_KEYS:
                    errors.append(
                        f'rule "{rule_id}": unknown selector key "{key}" '
                        f"(allowed: {sorted(SELECTOR_KEYS)})"
                    )

            retain_days, err = parse_duration(rule.get("retain_for", ""))
            if err:
                errors.append(f'rule "{rule_id}": {err}')
                continue

            redact_after = rule.get("redact_after")
            if redact_after is not None:
                redact_days, err = parse_duration(redact_after)
                if err:
                    errors.append(f'rule "{rule_id}": invalid redact_after: {err}')
                elif not redact_days < retain_days:
                    errors.append(
                        f'rule "{rule_id}": redact_after ({redact_after}) must be '
                        f"strictly less than retain_for ({rule.get('retain_for')})"
                    )

            sampling = rule.get("sampling")
            if sampling is not None:
                if sampling.get("alg") != SAMPLING_ALG_V1:
                    errors.append(
                        f'rule "{rule_id}": sampling.alg must be "{SAMPLING_ALG_V1}", '
                        f'got "{sampling.get("alg")}"'
                    )
                of = sampling.get("of")
                keep = sampling.get("keep")
                if not isinstance(of, int) or of < 1:
                    errors.append(f'rule "{rule_id}": sampling.of must be a positive integer')
                if not isinstance(keep, int) or keep < 1:
                    errors.append(f'rule "{rule_id}": sampling.keep must be a positive integer')
                if isinstance(of, int) and isinstance(keep, int) and keep > of:
                    errors.append(
                        f'rule "{rule_id}": sampling.keep ({keep}) must not exceed '
                        f"sampling.of ({of})"
                    )

            # Tier ceiling.
            if ceiling is not None and retain_days > ceiling:
                errors.append(
                    f'rule "{rule_id}": retain_for ({rule.get("retain_for")}) exceeds '
                    f"the {self.org_tier} tier ceiling ({ceiling:.0f} days)"
                )
            # Platform floor — no rule may retain less than this, any tier.
            if retain_days < PLATFORM_FLOOR_DAYS:
                errors.append(
                    f'rule "{rule_id}": retain_for ({rule.get("retain_for")}) is below '
                    f"the platform minimum retention floor ({PLATFORM_FLOOR_DAYS} days)"
                )
            # Regulated minimum.
            regulated = "regulated" in _as_set(selector.get("flow_tag", []))
            if regulated and retain_days < REGULATED_MIN_DAYS:
                errors.append(
                    f'rule "{rule_id}": flow_tag "regulated" requires a minimum '
                    f"retain_for of P6M ({REGULATED_MIN_DAYS} days)"
                )

    def _validate_catch_all(self, rules: list[dict], errors: list[str]) -> None:
        last_selector = rules[-1].get("selector") or {}
        if last_selector:
            errors.append(
                "policy must end with a terminal catch-all rule (empty selector {}); "
                "first-match evaluation without one leaves records unmatched"
            )
        for rule in rules[:-1]:
            if not (rule.get("selector") or {}):
                errors.append(
                    f'rule "{rule.get("rule_id")}" is a catch-all but not the last rule; '
                    "every rule after it is unreachable"
                )

    def _validate_shadowing(self, rules: list[dict], errors: list[str]) -> None:
        for j in range(len(rules)):
            for i in range(j):
                if _shadows(rules[i], rules[j]):
                    errors.append(
                        f'rule "{rules[j].get("rule_id")}" is fully shadowed by earlier '
                        f'rule "{rules[i].get("rule_id")}" and can never match'
                    )
                    break

    def _validate_broad_before_narrow(self, rules: list[dict], warnings: list[str]) -> None:
        for j in range(len(rules)):
            # The terminal catch-all is required to be last and overlaps every
            # rule by construction — warning about it would flag every valid
            # policy and train authors to ignore warnings.
            if not (rules[j].get("selector") or {}):
                continue
            for i in range(j):
                if _shadows(rules[i], rules[j]):
                    continue  # already an error, not a warning
                if _overlaps(rules[i], rules[j]):
                    warnings.append(
                        f'rule "{rules[i].get("rule_id")}" is broader than and precedes '
                        f'overlapping rule "{rules[j].get("rule_id")}"; the narrower rule '
                        "only matches records the broader one does not"
                    )
                    break

    def _validate_default_rule(self, body: RetentionPolicyCreate, errors: list[str]) -> None:
        default_rule = body.default_rule or {}
        retain_for = default_rule.get("retain_for")
        if not retain_for:
            errors.append("default_rule must include retain_for")
            return
        days, err = parse_duration(retain_for)
        if err:
            errors.append(f"default_rule: {err}")
            return
        ceiling = TIER_CEILINGS_DAYS[self.org_tier]
        if ceiling is not None and days > ceiling:
            errors.append(
                f"default_rule retain_for ({retain_for}) exceeds the {self.org_tier} "
                f"tier ceiling ({ceiling:.0f} days)"
            )
        if days < PLATFORM_FLOOR_DAYS:
            errors.append(
                f"default_rule retain_for ({retain_for}) is below the platform minimum "
                f"retention floor ({PLATFORM_FLOOR_DAYS} days)"
            )

    # ── Shortening friction ──────────────────────────────────────────

    def _validate_shortening(
        self, body: RetentionPolicyCreate, rules: list[dict], errors: list[str]
    ) -> None:
        if self.current_policy is None:
            return
        old_by_id = {rule.get("rule_id"): rule for rule in self.current_policy.rules or []}
        shortening = False
        for rule in rules:
            old = old_by_id.get(rule.get("rule_id"))
            if not isinstance(old, dict):
                continue
            old_days, old_err = parse_duration(old.get("retain_for", ""))
            new_days, new_err = parse_duration(rule.get("retain_for", ""))
            if old_err or new_err:
                continue  # duration errors already reported
            if new_days < old_days:
                shortening = True
                break
            old_redact = old.get("redact_after")
            new_redact = rule.get("redact_after")
            if not old_redact and new_redact:
                shortening = True
                break
        if not shortening:
            return

        distinct_approvers = {a.by for a in body.approvals if a.by}
        if len(distinct_approvers) < 2:
            errors.append(
                "this version shortens retention: dual approval by ≥2 distinct "
                "approver principals is required"
            )
        min_effective = self.now + SHORTENING_DELAY
        if body.effective_at is None:
            # Default shortening versions to the delayed effect; the caller
            # persists body.effective_at after validation.
            body.effective_at = min_effective
            return
        effective_at = body.effective_at
        if effective_at.tzinfo is None:
            effective_at = effective_at.replace(tzinfo=UTC)
        if effective_at < min_effective:
            errors.append(
                "this version shortens retention: effective_at must be at least "
                "7 days after creation"
            )
