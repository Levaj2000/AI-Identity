"""PolicyValidator — strict JSONB schema validation for policy rules.

SECURITY-CRITICAL: This module prevents malformed policy rules from
bypassing enforcement. Policies are the sole mechanism controlling what
agents can and cannot do. Invalid rules = broken security guarantees.

Design principles:
  - NEVER use eval() or exec(). All matching is declarative.
  - Whitelist-only: unknown keys are rejected, not silently ignored.
  - Depth-limited: prevents deeply nested payloads (max 3).
  - Size-limited: prevents oversized payloads (max 10KB).
  - Fail-closed: validation errors mean the policy is rejected.
"""

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("ai_identity.validation.policy")

# ── Constants ────────────────────────────────────────────────────────

MAX_RULES_DEPTH = 3
MAX_RULES_SIZE_BYTES = 10_240  # 10 KB
MAX_ENDPOINTS = 50
MAX_METHODS = 10
MAX_ENDPOINT_LENGTH = 256

# Recognized top-level keys in the rules dict.
# Any key not in this set is rejected.
ALLOWED_RULE_KEYS = frozenset({
    "allowed_endpoints",
    "denied_endpoints",
    "allowed_methods",
    "max_cost_usd",
})

# Valid HTTP methods (uppercase).
VALID_HTTP_METHODS = frozenset({
    "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS",
})

# Safe endpoint pattern: starts with / or *, contains only safe chars.
# No backticks, no null bytes, no control characters, no query strings.
_SAFE_ENDPOINT_RE = re.compile(r"^[a-zA-Z0-9/_\-.*]+$")


# ── Error Types ──────────────────────────────────────────────────────


@dataclass
class PolicyValidationError:
    """A single validation error found in the policy rules."""

    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of validating a policy rules dict."""

    valid: bool
    errors: list[PolicyValidationError] = field(default_factory=list)

    def add_error(self, field_name: str, message: str) -> None:
        """Record a validation error."""
        self.errors.append(PolicyValidationError(field=field_name, message=message))
        self.valid = False


# ── PolicyValidator ──────────────────────────────────────────────────


class PolicyValidator:
    """Strict JSONB schema validator for agent policy rules.

    Usage::

        validator = PolicyValidator()
        result = validator.validate(rules_dict)
        if not result.valid:
            raise HTTPException(400, detail=[e.__dict__ for e in result.errors])

    All validation is declarative — no eval(), no exec(), no code execution
    of any kind on the rules data.
    """

    def __init__(
        self,
        *,
        max_depth: int = MAX_RULES_DEPTH,
        max_size_bytes: int = MAX_RULES_SIZE_BYTES,
    ):
        self.max_depth = max_depth
        self.max_size_bytes = max_size_bytes

    def validate(self, rules: dict) -> ValidationResult:
        """Validate a policy rules dict.

        Checks (in order):
          1. Type check — must be a dict
          2. Size check — serialized JSON must be ≤ max_size_bytes
          3. Depth check — no nesting beyond max_depth
          4. Key whitelist — only recognized keys allowed
          5. Field-level validation for each known key

        Returns a ValidationResult with valid=True if all checks pass,
        or valid=False with a list of errors.
        """
        result = ValidationResult(valid=True)

        # 1. Type check
        if not isinstance(rules, dict):
            result.add_error("rules", f"Must be a dict, got {type(rules).__name__}")
            return result

        # 2. Size check (serialize to JSON to measure actual payload size)
        self._check_size(rules, result)
        if not result.valid:
            return result

        # 3. Depth check
        self._check_depth(rules, result)
        if not result.valid:
            return result

        # 4. Key whitelist
        self._check_unknown_keys(rules, result)

        # 5. Field-level validation
        self._validate_endpoints(rules, "allowed_endpoints", result)
        self._validate_endpoints(rules, "denied_endpoints", result)
        self._validate_methods(rules, result)
        self._validate_max_cost(rules, result)

        return result

    # ── Size Check ────────────────────────────────────────────────

    def _check_size(self, rules: dict, result: ValidationResult) -> None:
        """Reject payloads exceeding the max size."""
        try:
            serialized = json.dumps(rules, default=str)
        except (TypeError, ValueError) as exc:
            result.add_error("rules", f"Cannot serialize to JSON: {exc}")
            return

        size = len(serialized.encode("utf-8"))
        if size > self.max_size_bytes:
            result.add_error(
                "rules",
                f"Rules payload too large: {size} bytes "
                f"(max {self.max_size_bytes} bytes)",
            )

    # ── Depth Check ───────────────────────────────────────────────

    def _check_depth(self, rules: dict, result: ValidationResult) -> None:
        """Reject payloads with nesting deeper than max_depth."""
        depth = self._measure_depth(rules)
        if depth > self.max_depth:
            result.add_error(
                "rules",
                f"Rules nesting too deep: depth {depth} "
                f"(max {self.max_depth})",
            )

    @staticmethod
    def _measure_depth(obj: object, current: int = 1) -> int:
        """Measure the nesting depth of a JSON-like structure.

        A flat dict like {"a": 1} has depth 1.
        {"a": {"b": 1}} has depth 2.
        {"a": [{"b": 1}]} has depth 3.
        """
        if isinstance(obj, dict):
            if not obj:
                return current
            return max(
                PolicyValidator._measure_depth(v, current + 1)
                for v in obj.values()
            )
        if isinstance(obj, list):
            if not obj:
                return current
            return max(
                PolicyValidator._measure_depth(item, current + 1)
                for item in obj
            )
        return current

    # ── Key Whitelist ─────────────────────────────────────────────

    def _check_unknown_keys(self, rules: dict, result: ValidationResult) -> None:
        """Reject any key not in the allowed set."""
        unknown = set(rules.keys()) - ALLOWED_RULE_KEYS
        if unknown:
            for key in sorted(unknown):
                result.add_error(
                    key,
                    f"Unknown rule key '{key}'. "
                    f"Allowed keys: {sorted(ALLOWED_RULE_KEYS)}",
                )

    # ── Endpoint Validation ───────────────────────────────────────

    def _validate_endpoints(
        self, rules: dict, field_name: str, result: ValidationResult
    ) -> None:
        """Validate an endpoint list field (allowed_endpoints or denied_endpoints)."""
        if field_name not in rules:
            return

        endpoints = rules[field_name]

        # Must be a list
        if not isinstance(endpoints, list):
            result.add_error(
                field_name,
                f"Must be a list, got {type(endpoints).__name__}",
            )
            return

        # Size cap
        if len(endpoints) > MAX_ENDPOINTS:
            result.add_error(
                field_name,
                f"Too many endpoints: {len(endpoints)} (max {MAX_ENDPOINTS})",
            )
            return

        for i, ep in enumerate(endpoints):
            # Must be a string
            if not isinstance(ep, str):
                result.add_error(
                    f"{field_name}[{i}]",
                    f"Must be a string, got {type(ep).__name__}",
                )
                continue

            # Length cap
            if len(ep) > MAX_ENDPOINT_LENGTH:
                result.add_error(
                    f"{field_name}[{i}]",
                    f"Endpoint too long: {len(ep)} chars (max {MAX_ENDPOINT_LENGTH})",
                )
                continue

            # Empty string
            if not ep:
                result.add_error(f"{field_name}[{i}]", "Endpoint cannot be empty")
                continue

            # Must start with / or be exactly *
            if ep != "*" and not ep.startswith("/"):
                result.add_error(
                    f"{field_name}[{i}]",
                    f"Endpoint must start with '/' or be '*', got '{ep}'",
                )
                continue

            # Safe characters only — prevent injection
            if not _SAFE_ENDPOINT_RE.match(ep):
                result.add_error(
                    f"{field_name}[{i}]",
                    f"Endpoint contains unsafe characters: '{ep}'",
                )

    # ── Method Validation ─────────────────────────────────────────

    def _validate_methods(self, rules: dict, result: ValidationResult) -> None:
        """Validate the allowed_methods field."""
        if "allowed_methods" not in rules:
            return

        methods = rules["allowed_methods"]

        if not isinstance(methods, list):
            result.add_error(
                "allowed_methods",
                f"Must be a list, got {type(methods).__name__}",
            )
            return

        if len(methods) > MAX_METHODS:
            result.add_error(
                "allowed_methods",
                f"Too many methods: {len(methods)} (max {MAX_METHODS})",
            )
            return

        for i, method in enumerate(methods):
            if not isinstance(method, str):
                result.add_error(
                    f"allowed_methods[{i}]",
                    f"Must be a string, got {type(method).__name__}",
                )
                continue

            if method.upper() not in VALID_HTTP_METHODS:
                result.add_error(
                    f"allowed_methods[{i}]",
                    f"Invalid HTTP method '{method}'. "
                    f"Valid methods: {sorted(VALID_HTTP_METHODS)}",
                )

    # ── Cost Validation ───────────────────────────────────────────

    def _validate_max_cost(self, rules: dict, result: ValidationResult) -> None:
        """Validate the max_cost_usd field."""
        if "max_cost_usd" not in rules:
            return

        cost = rules["max_cost_usd"]

        if not isinstance(cost, (int, float)):
            result.add_error(
                "max_cost_usd",
                f"Must be a number, got {type(cost).__name__}",
            )
            return

        if cost < 0:
            result.add_error("max_cost_usd", "Cannot be negative")

        if cost > 10_000:
            result.add_error(
                "max_cost_usd",
                f"Unreasonably high: ${cost} (max $10,000)",
            )
