"""Fail-closed gateway enforcement — deny on policy error or timeout.

SECURITY-CRITICAL: This module implements the fail-closed pattern for SOC 2
compliance. Every request must be evaluated against the agent's policy before
forwarding. The cardinal rule: **when in doubt, deny.**

Fail-closed guarantees:
  - Policy engine unreachable → DENY (503)
  - Policy evaluation times out (>500ms) → DENY
  - Policy evaluation raises any exception → DENY
  - No active policy found for agent → DENY
  - Circuit breaker open (5 failures in 60s) → DENY ALL + alert
  - Agent not found or revoked → DENY (401)
  - Agent on blocklist → DENY (403)

Only an explicit ALLOW from a successful policy evaluation permits a request.
"""

import enum
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass

from sqlalchemy.orm import Session

from common.audit import create_audit_entry
from common.config.settings import settings
from common.models import Agent, Policy
from common.models.blocked_agent import BlockedAgent
from gateway.app.circuit_breaker import CircuitBreaker

logger = logging.getLogger("ai_identity.gateway.enforce")

# Module-level circuit breaker for the policy engine.
# Single instance shared across all requests (thread-safe).
policy_circuit_breaker = CircuitBreaker(name="policy-engine")

# Thread pool for timeout-bounded policy evaluation.
# Max 4 workers — policy evaluation should be fast (DB read + rule check).
_policy_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="policy-eval")


# ── Decision Types ────────────────────────────────────────────────────


class Decision(enum.StrEnum):
    """Gateway enforcement decisions for audit logging."""

    ALLOW = "allow"
    DENY = "deny"
    ERROR = "error"
    PENDING_APPROVAL = "pending_approval"


class DenyReason(enum.StrEnum):
    """Why a request was denied — included in response and audit log."""

    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    POLICY_TIMEOUT = "policy_eval_timeout"
    POLICY_ERROR = "policy_eval_error"
    NO_ACTIVE_POLICY = "no_active_policy"
    POLICY_DENIED = "policy_denied"
    AGENT_NOT_FOUND = "agent_not_found"
    AGENT_INACTIVE = "agent_inactive"
    AGENT_BLOCKED = "agent_blocked"
    RUNTIME_KEY_ON_MANAGEMENT = "runtime_key_on_management_endpoint"
    ADMIN_KEY_ON_RUNTIME = "admin_key_on_runtime_endpoint"


@dataclass
class EnforcementResult:
    """Result of gateway enforcement — drives the response to the agent."""

    decision: Decision
    deny_reason: DenyReason | None = None
    status_code: int = 200
    message: str = "Request allowed"
    agent_id: uuid.UUID | None = None
    review_id: str | None = None  # Set when HITL approval is required

    @property
    def allowed(self) -> bool:
        """Convenience check — only explicit ALLOW permits the request."""
        return self.decision == Decision.ALLOW

    @property
    def pending(self) -> bool:
        """Check if request is waiting for human approval."""
        return self.decision == Decision.PENDING_APPROVAL


# ── Policy Evaluation (Timeout-Bounded) ──────────────────────────────


def _evaluate_policy_rules(rules: dict, endpoint: str, method: str) -> bool:
    """Evaluate policy rules against the request.

    This is a simple rule engine for MVP. Rules are a JSONB dict with:
      - allowed_endpoints: list of endpoint patterns (glob-style)
      - allowed_methods: list of HTTP methods
      - denied_endpoints: explicit deny list (checked first)
      - max_cost_usd: maximum cost per request (future)

    Returns True if the request is allowed, False if denied.

    SECURITY: Default is DENY. The request is only allowed if at least
    one rule explicitly permits it and no rule explicitly denies it.
    """
    # Empty rules = no permissions granted = DENY
    if not rules:
        return False

    # Check explicit deny list first
    denied_endpoints = rules.get("denied_endpoints", [])
    for pattern in denied_endpoints:
        if _endpoint_matches(endpoint, pattern):
            return False

    # Check allowed endpoints
    allowed_endpoints = rules.get("allowed_endpoints", [])
    if allowed_endpoints:
        endpoint_allowed = any(
            _endpoint_matches(endpoint, pattern) for pattern in allowed_endpoints
        )
        if not endpoint_allowed:
            return False
    else:
        # No allowed_endpoints specified = nothing is allowed (fail-closed)
        return False

    # Check allowed methods
    allowed_methods = rules.get("allowed_methods", [])
    return not (allowed_methods and method.upper() not in [m.upper() for m in allowed_methods])


def _endpoint_matches(endpoint: str, pattern: str) -> bool:
    """Simple endpoint matching with wildcard support.

    Supports:
      - Exact match: "/v1/chat" matches "/v1/chat"
      - Prefix wildcard: "/v1/*" matches "/v1/chat" and "/v1/embeddings"
      - Full wildcard: "*" matches everything
    """
    if pattern == "*":
        return True
    if pattern.endswith("/*"):
        prefix = pattern[:-1]  # "/v1/" from "/v1/*"
        return endpoint.startswith(prefix) or endpoint == pattern[:-2]
    return endpoint == pattern


def _load_and_evaluate_policy(
    db: Session,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
) -> bool:
    """Load the agent's active policy and evaluate it.

    This function runs inside a thread pool with a timeout.
    Any exception here is caught by the caller and treated as DENY.

    Returns True if allowed, False if denied.
    """
    from common.validation.policy import PolicyValidator

    # Load active policy for the agent
    policy = (
        db.query(Policy)
        .filter(Policy.agent_id == agent_id, Policy.is_active.is_(True))
        .order_by(Policy.version.desc())
        .first()
    )

    if policy is None:
        # No active policy = fail-closed = DENY
        return False

    # Defense-in-depth: validate rules even from the DB.
    # Malformed rules that somehow bypassed creation validation
    # must not be evaluated — fail-closed = DENY.
    validation = PolicyValidator().validate(policy.rules)
    if not validation.valid:
        error_summary = "; ".join(f"{e.field}: {e.message}" for e in validation.errors)
        logger.warning(
            "Policy %d for agent %s has invalid rules — DENIED: %s",
            policy.id,
            agent_id,
            error_summary,
        )
        return False

    return _evaluate_policy_rules(policy.rules, endpoint, method)


# ── Key-Type Endpoint Classification ─────────────────────────────────

# Management endpoints — require aid_admin_ keys.
# These are the identity/policy management API paths.
MANAGEMENT_PREFIXES = (
    "/api/v1/agents",
    "/api/v1/policies",
    "/api/v1/audit",
    "/api/v1/users",
)


def _is_management_endpoint(endpoint: str) -> bool:
    """Check if an endpoint is a management/admin endpoint.

    Management endpoints include agent CRUD, key management,
    policy management, audit log access, and user management.
    """
    return any(endpoint.startswith(prefix) for prefix in MANAGEMENT_PREFIXES)


def _check_key_type(key_type: str | None, endpoint: str) -> EnforcementResult | None:
    """Enforce key-type / endpoint separation.

    Returns an EnforcementResult if the key type is forbidden for this
    endpoint, or None if the key type is allowed.

    Rules:
      - runtime keys (aid_sk_) → ONLY runtime/proxy endpoints
      - admin keys (aid_admin_) → ONLY management endpoints
      - No key_type (legacy) → allowed everywhere (backward compat)
    """
    if key_type is None:
        return None  # Legacy key — no restriction (backward compat)

    is_mgmt = _is_management_endpoint(endpoint)

    if key_type == "runtime" and is_mgmt:
        return EnforcementResult(
            decision=Decision.DENY,
            deny_reason=DenyReason.RUNTIME_KEY_ON_MANAGEMENT,
            status_code=403,
            message="Runtime key (aid_sk_) cannot access management endpoints",
        )

    if key_type == "admin" and not is_mgmt:
        return EnforcementResult(
            decision=Decision.DENY,
            deny_reason=DenyReason.ADMIN_KEY_ON_RUNTIME,
            status_code=403,
            message="Admin key (aid_admin_) cannot access runtime/proxy endpoints",
        )

    return None


# ── Main Enforcement Function ────────────────────────────────────────


def enforce(
    db: Session,
    *,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    key_type: str | None = None,
    request_metadata: dict | None = None,
) -> EnforcementResult:
    """Evaluate whether an agent's request should be allowed or denied.

    This is the fail-closed gateway core. The evaluation flow:

    1. Check circuit breaker — if OPEN, deny immediately (503)
    1b. Check blocklist — if agent is blocked, deny (403)
    2. Verify agent exists and is active
    3. Load + evaluate policy (with timeout)
       - Timeout → record failure, deny
       - Exception → record failure, deny
       - No active policy → deny
       - Policy denies → deny
       - Policy allows → allow
    4. Record success/failure for circuit breaker
    5. Write audit log entry

    Args:
        db: Database session.
        agent_id: UUID of the requesting agent.
        endpoint: Target API endpoint (e.g., "/v1/chat").
        method: HTTP method (e.g., "POST").
        key_type: "runtime" or "admin" — determines which endpoints are accessible.
        request_metadata: Optional context for the audit log.

    Returns:
        EnforcementResult with decision, status code, and message.
    """
    metadata = request_metadata if request_metadata is not None else {}

    # ── 0. Key-type enforcement (checked FIRST, before circuit breaker) ──
    key_type_result = _check_key_type(key_type, endpoint)
    if key_type_result is not None:
        key_type_result.agent_id = agent_id
        metadata["key_type"] = key_type or "unknown"
        _audit_decision(db, key_type_result, endpoint, method, metadata)
        return key_type_result

    # ── 1. Circuit breaker check ──────────────────────────────────
    if not policy_circuit_breaker.can_execute():
        result = EnforcementResult(
            decision=Decision.ERROR,
            deny_reason=DenyReason.CIRCUIT_BREAKER_OPEN,
            status_code=503,
            message="Service unavailable: policy engine circuit breaker is open",
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    # ── 1b. Blocklist check ──────────────────────────────────────
    blocked = db.query(BlockedAgent).filter(BlockedAgent.agent_id == str(agent_id)).first()
    if blocked is not None:
        metadata["blocked_reason"] = blocked.reason or "no reason provided"
        metadata["shadow_agent"] = True
        result = EnforcementResult(
            decision=Decision.DENY,
            deny_reason=DenyReason.AGENT_BLOCKED,
            status_code=403,
            message="Agent is blocked — requests not permitted",
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    # ── 2. Agent validation ───────────────────────────────────────
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        result = EnforcementResult(
            decision=Decision.DENY,
            deny_reason=DenyReason.AGENT_NOT_FOUND,
            status_code=404,
            message="Agent not found",
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    if agent.status != "active":
        result = EnforcementResult(
            decision=Decision.DENY,
            deny_reason=DenyReason.AGENT_INACTIVE,
            status_code=403,
            message=f"Agent is {agent.status} — requests not permitted",
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    # ── 3. Policy evaluation with timeout ─────────────────────────
    timeout_seconds = settings.policy_eval_timeout_ms / 1000.0

    try:
        future = _policy_executor.submit(
            _load_and_evaluate_policy,
            db,
            agent_id,
            endpoint,
            method,
        )
        policy_allows = future.result(timeout=timeout_seconds)

    except TimeoutError:
        # Policy evaluation took too long — fail-closed
        policy_circuit_breaker.record_failure()
        logger.warning(
            "Policy evaluation TIMEOUT for agent %s (>%dms) — DENIED",
            agent_id,
            settings.policy_eval_timeout_ms,
        )
        result = EnforcementResult(
            decision=Decision.ERROR,
            deny_reason=DenyReason.POLICY_TIMEOUT,
            status_code=503,
            message=f"Policy evaluation timed out ({settings.policy_eval_timeout_ms}ms)",
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    except Exception:
        # Any other error — fail-closed
        policy_circuit_breaker.record_failure()
        logger.exception(
            "Policy evaluation ERROR for agent %s — DENIED",
            agent_id,
        )
        result = EnforcementResult(
            decision=Decision.ERROR,
            deny_reason=DenyReason.POLICY_ERROR,
            status_code=503,
            message="Policy evaluation failed — request denied",
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    # ── 4. Record outcome on circuit breaker ──────────────────────
    policy_circuit_breaker.record_success()

    if not policy_allows:
        # Policy explicitly denied or no active policy
        # Check if it was no-policy vs policy-denied
        policy = (
            db.query(Policy).filter(Policy.agent_id == agent_id, Policy.is_active.is_(True)).first()
        )
        if policy is None:
            deny_reason = DenyReason.NO_ACTIVE_POLICY
            message = "No active policy — request denied (fail-closed)"
        else:
            deny_reason = DenyReason.POLICY_DENIED
            message = "Request denied by policy"

        result = EnforcementResult(
            decision=Decision.DENY,
            deny_reason=deny_reason,
            status_code=403,
            message=message,
            agent_id=agent_id,
        )
        _audit_decision(db, result, endpoint, method, metadata)
        return result

    # ── 5. ALLOW — the only path where a request goes through ─────
    result = EnforcementResult(
        decision=Decision.ALLOW,
        deny_reason=None,
        status_code=200,
        message="Request allowed",
        agent_id=agent_id,
    )
    _audit_decision(db, result, endpoint, method, metadata)
    return result


# ── Audit Logging ─────────────────────────────────────────────────────


def _audit_decision(
    db: Session,
    result: EnforcementResult,
    endpoint: str,
    method: str,
    metadata: dict,
) -> None:
    """Write an audit log entry for every enforcement decision.

    SECURITY: Every request — allowed, denied, or errored — must be logged
    with the HMAC integrity chain for SOC 2 compliance.
    """
    if result.agent_id is None:
        return

    audit_metadata = {**metadata}
    if result.deny_reason:
        audit_metadata["deny_reason"] = result.deny_reason.value
    audit_metadata["status_code"] = result.status_code

    try:
        create_audit_entry(
            db,
            agent_id=result.agent_id,
            endpoint=endpoint,
            method=method,
            decision=result.decision.value,
            request_metadata=audit_metadata,
        )
    except Exception:
        # Audit write failure is logged but MUST NOT change the decision.
        # The enforcement decision was already made — we just couldn't record it.
        logger.exception(
            "CRITICAL: Failed to write audit entry for agent %s — "
            "decision was %s but audit trail has a gap",
            result.agent_id,
            result.decision.value,
        )
