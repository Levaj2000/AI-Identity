"""Pydantic schemas for Agent CRUD operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from common.validation.eu_ai_act import validate_risk_class

# ── User Schemas ─────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Request body for creating a new user."""

    email: str = Field(..., max_length=255)
    org_id: str | None = None
    role: str = "owner"


class UserResponse(BaseModel):
    """Response body for user details."""

    id: uuid.UUID
    email: str
    org_id: str | None
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Agent Schemas ────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    """Request body for creating a new agent.

    Only `name` is required. Capabilities and metadata are optional and
    default to an empty list and empty dict respectively.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the agent",
        examples=["Customer Support Bot"],
    )
    description: str | None = Field(
        None,
        description="Optional description of the agent's purpose",
        examples=["Handles tier-1 support tickets via chat"],
    )
    capabilities: list = Field(
        default_factory=list,
        description="Structured list of what the agent can do",
        examples=[["chat_completion", "function_calling"]],
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Freeform key-value pairs for filtering and grouping",
        examples=[{"framework": "langchain", "environment": "production"}],
    )
    eu_ai_act_risk_class: str | None = Field(
        None,
        description=(
            "EU AI Act Annex III category code (e.g. '3(a)', '4(b)') or "
            "'not_in_scope' if the deployer has determined this agent is "
            "not a high-risk system under Annex III. `null` means not "
            "classified yet. Consumed by the compliance export builder."
        ),
        examples=["4(b)", "not_in_scope"],
    )

    @field_validator("eu_ai_act_risk_class")
    @classmethod
    def _validate_risk_class(cls, v: str | None) -> str | None:
        return validate_risk_class(v)


class AgentUpdate(BaseModel):
    """Request body for updating an agent. All fields are optional — only
    include the fields you want to change.
    """

    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="New name for the agent",
    )
    description: str | None = Field(
        None,
        description="New description",
    )
    capabilities: list | None = Field(
        None,
        description="Replace the agent's capabilities list",
        examples=[["chat_completion", "embeddings"]],
    )
    metadata: dict | None = Field(
        None,
        description="Replace the agent's metadata dict",
        examples=[{"environment": "staging", "owner_team": "platform"}],
    )
    status: str | None = Field(
        None,
        pattern="^(active|suspended)$",
        description="Set agent status (active or suspended). Use DELETE to revoke.",
    )
    eu_ai_act_risk_class: str | None = Field(
        None,
        description=(
            "Update the EU AI Act Annex III classification. Pass an Annex "
            "III category code, 'not_in_scope', or omit to leave unchanged. "
            "There is no way to clear a previously-set classification via "
            "this endpoint — that would require explicit auditor review."
        ),
        examples=["3(a)"],
    )

    @field_validator("eu_ai_act_risk_class")
    @classmethod
    def _validate_risk_class(cls, v: str | None) -> str | None:
        return validate_risk_class(v)


class AgentResponse(BaseModel):
    """Full agent details returned by GET, PUT, and DELETE endpoints."""

    id: uuid.UUID = Field(description="Unique agent identifier")
    user_id: uuid.UUID = Field(description="ID of the owning user")
    org_id: uuid.UUID | None = Field(None, description="ID of the owning organization")
    name: str = Field(description="Human-readable agent name")
    description: str | None = Field(description="Agent description")
    status: str = Field(description="Current status: active, suspended, or revoked")
    capabilities: list = Field(description="List of agent capabilities")
    metadata: dict = Field(description="Freeform key-value metadata")
    eu_ai_act_risk_class: str | None = Field(
        None,
        description=(
            "EU AI Act Annex III category code, 'not_in_scope', or null if not yet classified."
        ),
    )
    created_at: datetime = Field(description="When the agent was created")
    updated_at: datetime = Field(description="When the agent was last modified")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
                    "name": "Customer Support Bot",
                    "description": "Handles tier-1 support tickets",
                    "status": "active",
                    "capabilities": ["chat_completion", "function_calling"],
                    "metadata": {"framework": "langchain", "environment": "production"},
                    "eu_ai_act_risk_class": "4(b)",
                    "created_at": "2026-03-10T12:00:00Z",
                    "updated_at": "2026-03-10T12:00:00Z",
                }
            ]
        },
    }


class AgentListResponse(BaseModel):
    """Paginated list of agents."""

    items: list[AgentResponse] = Field(description="List of agents")
    total: int = Field(description="Total number of matching agents")
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")


class AgentCreateResponse(BaseModel):
    """Response for agent creation — includes the show-once plaintext API key.

    **Important:** The `api_key` field is only returned at creation time.
    Store it securely — it cannot be retrieved again.
    """

    agent: AgentResponse
    api_key: str = Field(
        ...,
        description="Plaintext API key (aid_sk_…) — shown only once at creation time",
        examples=["aid_sk_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"],
    )


# ── Capability Schemas ───────────────────────────────────────────────────


class CapabilityResponse(BaseModel):
    """A predefined capability with its endpoint permission mappings."""

    id: str = Field(description="Capability identifier (e.g. openai_chat)")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="What this capability grants access to")
    endpoints: list[str] = Field(description="Allowed API endpoint patterns")
    methods: list[str] = Field(description="Allowed HTTP methods")


# ── Agent Key Schemas ────────────────────────────────────────────────────


class AgentKeyResponse(BaseModel):
    """Agent key metadata. The full key and hash are never exposed."""

    id: int = Field(description="Key ID")
    agent_id: uuid.UUID = Field(description="Agent this key belongs to")
    key_prefix: str = Field(
        description="First 12 characters of the key for identification",
        examples=["aid_sk_a1b2"],
    )
    key_type: str = Field(
        description="Key type: runtime (aid_sk_) for proxy endpoints, admin (aid_admin_) for management",
        examples=["runtime"],
    )
    status: str = Field(
        description="Key status: active, rotated, or revoked",
        examples=["active"],
    )
    expires_at: datetime | None = Field(
        description="When the key expires (set during rotation grace period)",
    )
    created_at: datetime = Field(description="When the key was created")

    model_config = {"from_attributes": True}


class AgentKeyCreateResponse(BaseModel):
    """Response for key creation — includes the show-once plaintext key.

    **Important:** Store the `api_key` securely. It cannot be retrieved after
    this response.
    """

    key: AgentKeyResponse
    api_key: str = Field(
        ...,
        description="Plaintext API key (aid_sk_…) — shown only once",
        examples=["aid_sk_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"],
    )


class AgentKeyListResponse(BaseModel):
    """List of agent keys with prefix and status (never the full key)."""

    items: list[AgentKeyResponse] = Field(description="List of keys")
    total: int = Field(description="Total number of keys")


class AgentKeyRotateResponse(BaseModel):
    """Response for key rotation. The old key enters a 24-hour grace period
    (status=rotated) before being automatically revoked.
    """

    new_key: AgentKeyResponse = Field(description="The newly generated key")
    api_key: str = Field(
        ...,
        description="Plaintext API key for the new key — shown only once",
        examples=["aid_sk_f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8"],
    )
    rotated_key: AgentKeyResponse = Field(
        description="The old key, now with status=rotated and a 24hr expiry",
    )


class AgentKeyRefreshResponse(BaseModel):
    """Response for routine key refresh — roll a near-expiry key to a fresh one.

    Same grace mechanics as rotation: the previous key stays valid
    (status=rotated) for the grace window so the client can switch over without
    downtime, and the new key carries a fresh TTL.
    """

    new_key: AgentKeyResponse = Field(description="The newly issued key")
    api_key: str = Field(
        ...,
        description="Plaintext API key for the new key — shown only once",
        examples=["aid_sk_f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8"],
    )
    previous_key: AgentKeyResponse = Field(
        description="The prior key, now status=rotated with a grace-period expiry",
    )


# ── Policy Schemas ───────────────────────────────────────────────────────


class PolicyCreate(BaseModel):
    """Request body for creating a policy.

    Rules are validated against a strict schema: only recognized keys are
    allowed, nesting is capped at depth 3, payload size at 10KB, and all
    endpoint patterns and HTTP methods are checked.
    """

    rules: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rules(self) -> "PolicyCreate":
        """Run PolicyValidator on the rules dict at creation time."""
        from common.validation.policy import PolicyValidator

        validator = PolicyValidator()
        result = validator.validate(self.rules)
        if not result.valid:
            errors = "; ".join(f"{e.field}: {e.message}" for e in result.errors)
            msg = f"Invalid policy rules: {errors}"
            raise ValueError(msg)
        return self


class PolicyResponse(BaseModel):
    """Response body for a policy.

    ``warnings`` is populated on creation / update paths when the validator
    produces non-fatal concerns (e.g. a ``when`` clause referencing a
    metadata key the agent hasn't been tagged with). It is ``None`` on
    read paths — warnings are ephemeral authoring context, not state.
    """

    id: int
    agent_id: uuid.UUID
    rules: dict
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    warnings: list[dict[str, str]] | None = Field(
        default=None,
        description=(
            "Non-fatal validation concerns surfaced at creation time. "
            "Each entry: {field, message}. `null` on read paths."
        ),
    )

    model_config = {"from_attributes": True}


# ── Audit Log Schemas ────────────────────────────────────────────────────


class AuditLogResponse(BaseModel):
    """Response body for an audit log entry with HMAC integrity fields."""

    id: int
    agent_id: uuid.UUID
    user_id: uuid.UUID | None = None
    org_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Tenant org this entry belongs to. Populated from agent.org_id at "
            "write time; sentinel system-org for orphan/shadow entries."
        ),
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "End-to-end request ID. One value travels client → API → gateway → "
            "audit row, so operators can reconstruct a single user action across "
            "services with a point query."
        ),
    )
    endpoint: str
    method: str
    decision: str
    cost_estimate_usd: float | None
    latency_ms: int | None
    request_metadata: dict
    entry_hash: str = Field(description="HMAC-SHA256 of this entry's canonical data")
    prev_hash: str = Field(description="entry_hash of the preceding entry (GENESIS for first)")
    prev_hash_org: str | None = Field(
        default=None,
        description=(
            "entry_hash_org of the preceding row in this org's chain "
            "(GENESIS for the org's first row). Nullable on rows written "
            "before the per-org chain migration; NOT NULL after Phase 2b."
        ),
    )
    entry_hash_org: str | None = Field(
        default=None,
        description=(
            "HMAC-SHA256 of canonical data + prev_hash_org. The per-org "
            "chain field the offline CLI verifier walks to prove tenant-"
            "scoped integrity without depending on other tenants' rows."
        ),
    )
    org_chain_seq: int | None = Field(
        default=None,
        description=(
            "1-based monotonic sequence within org_id. Lets the verifier "
            "prove no rows were deleted from this org's history — a gap "
            "in the sequence is a completeness violation."
        ),
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditLogResponse] = Field(description="List of audit entries")
    total: int = Field(description="Total number of matching entries")
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")


class AuditChainVerifyResponse(BaseModel):
    """Result of audit chain integrity verification."""

    valid: bool = Field(description="True if the entire chain is intact")
    total_entries: int = Field(description="Total entries in the chain")
    entries_verified: int = Field(description="Entries successfully verified")
    first_broken_id: int | None = Field(
        None, description="ID of the first entry with a broken hash (if any)"
    )
    message: str = Field(description="Human-readable verification result")


# ── Forensics Schemas ────────────────────────────────────────────────────


class TopEndpoint(BaseModel):
    """An endpoint with its request count."""

    endpoint: str
    count: int


class AuditStatsResponse(BaseModel):
    """Aggregated statistics for audit log entries over a time window."""

    total_events: int = Field(description="Total audit entries in window")
    allowed_count: int = Field(description="Number of allowed requests")
    denied_count: int = Field(description="Number of denied requests")
    error_count: int = Field(description="Number of error requests")
    total_cost_usd: float = Field(description="Sum of cost_estimate_usd")
    avg_latency_ms: float | None = Field(description="Average latency in ms")
    top_endpoints: list[TopEndpoint] = Field(description="Top 10 endpoints by request count")


class AuditReconstructResponse(BaseModel):
    """Incident reconstruction: events + context for a time window."""

    agent_id: uuid.UUID
    agent_name: str | None = None
    start_date: datetime
    end_date: datetime
    events: list[AuditLogResponse] = Field(description="All events in window")
    chain_verification: AuditChainVerifyResponse
    active_policy: PolicyResponse | None = Field(
        None, description="Active policy at time of investigation"
    )
    stats: AuditStatsResponse


class ReliabilityStatement(BaseModel):
    """Plain-English reliability statement for a forensics report.

    Drafted to support a FRE 702 / Daubert reliability showing and ISO/IEC 27037
    evidence-acquisition documentation: how integrity is established, what the
    signature attests, and how a relying party can verify it independently. Honest
    about the current symmetric-key (key-holder) verification model.
    """

    method: str = Field(description="How tamper-evidence and completeness are established")
    signature_covers: str = Field(description="What the report signature attests")
    timestamp_source: str = Field(description="Source and basis of timestamps")
    independent_verification: str = Field(description="How a relying party verifies, offline")
    limitations: str = Field(description="Honest scope of what the proof does and does not show")
    standards_alignment: str = Field(description="Evidentiary standards the format targets")
    statement: str = Field(description="One-paragraph prose summary for the record")


class ForensicsReportResponse(BaseModel):
    """Exportable forensics report with chain-of-custody certificate."""

    report_id: str = Field(description="Unique report identifier")
    generated_at: datetime
    agent: dict | None = Field(
        default=None,
        description="Agent details (present for agent-scoped exports; null for org-wide / incident scope)",
    )
    scope: dict = Field(
        default_factory=dict,
        description=(
            "Export scope descriptor: {type: 'agent'|'incident'|'org', plus identifiers}. "
            "States on the face of the Case File exactly what the evidence set covers."
        ),
    )
    time_window: dict = Field(description="Start and end timestamps")
    events: list[AuditLogResponse]
    chain_verification: AuditChainVerifyResponse
    active_policy: PolicyResponse | None = None
    stats: AuditStatsResponse
    report_signature: str = Field(
        description=(
            "HMAC-SHA256 signature of report_id + generated_at + chain_verification fields. "
            "Recompute with verify_report_signature() to confirm this report was produced "
            "by AI Identity and has not been altered since export."
        )
    )
    reliability_statement: ReliabilityStatement | None = Field(
        default=None,
        description="Plain-English reliability statement for FRE 702 / ISO 27037 use.",
    )


# ── AI Summary (Perplexity) ─────────────────────────────────────────────


class AuditSummaryRequest(BaseModel):
    """Request body for AI-generated audit summary."""

    event_ids: list[int] | None = Field(None, description="Specific event IDs to summarize")
    agent_id: uuid.UUID | None = Field(None, description="Filter by agent")
    start_date: datetime | None = Field(None, description="Window start")
    end_date: datetime | None = Field(None, description="Window end")
    decision: str | None = Field(None, description="Filter by decision (allow/deny/error)")
    endpoint: str | None = Field(None, description="Filter by endpoint (partial match)")
    action_type: str | None = Field(None, description="Filter by metadata action_type")
    model: str | None = Field(None, description="Filter by metadata model")
    cost_min: float | None = Field(None, description="Minimum cost_estimate_usd")
    cost_max: float | None = Field(None, description="Maximum cost_estimate_usd")
    focus_hint: str | None = Field(
        None,
        max_length=500,
        description=(
            "Optional analyst intent hint forwarded to the LLM "
            "(e.g. 'Explain this deny cluster', 'Why was this single event denied?'). "
            "Used to focus the analysis without changing the JSON schema. "
            "Lens-style prompts (denials, anomalies, actor timeline) typically "
            "run 200-400 chars, so the cap is generous to avoid silent 422s."
        ),
    )
    max_events: int = Field(100, ge=1, le=500, description="Max events to include in summary")


class ObservedFact(BaseModel):
    """A single observed fact from the audit analysis."""

    label: str
    value: str


class SummaryFacts(BaseModel):
    """Deterministic numeric facts computed server-side from the audit DB.

    These are the authoritative source for any number shown in the AI summary
    panel. They are produced by the same query that backs the KPI bar, so the
    two views can never disagree. The LLM is explicitly forbidden from
    populating these fields; it only writes prose around them.
    """

    time_window_start: datetime | None = Field(
        None,
        description=(
            "Start of the aggregate window used to compute counts. None when "
            "no defined window applies (e.g. single-event analysis with no "
            "available neighborhood)."
        ),
    )
    time_window_end: datetime | None = Field(
        None, description="End of the aggregate window used to compute counts."
    )
    total_requests: int | None = Field(
        None,
        description=(
            "Total audit events in the aggregate window. None when no "
            "window applies — frontend renders 'not available'."
        ),
    )
    requests_allowed: int | None = Field(None, description="Allowed-decision count.")
    requests_denied: int | None = Field(None, description="Denied-decision count.")
    errors: int | None = Field(None, description="Error-decision count.")
    aggregate_window_source: str = Field(
        description=(
            "How the aggregate window was derived. One of: "
            "'filter' (the user's filter scope), "
            "'event_neighborhood' (±24h around a single event when no filter window was set), "
            "'unavailable' (no aggregate computable — counts will be None)."
        )
    )


class AuditSummaryResponse(BaseModel):
    """Structured AI-generated audit summary (v2).

    `facts` carries deterministic numeric counts computed server-side from
    the same query as the KPI bar. The frontend MUST render numeric fields
    from `facts` directly — `observed_facts` and the LLM-generated prose
    fields are not permitted to contradict them.
    """

    title: str = Field(description="Report title")
    executive_summary: str = Field(description="2-4 sentence overview")
    facts: SummaryFacts = Field(
        description="Deterministic numeric facts (same query as the KPI bar)"
    )
    observed_facts: list[ObservedFact] = Field(
        description=(
            "Key-value fact rows. The first rows are populated by the server "
            "from `facts` and are guaranteed to match the KPI bar. Any rows "
            "the LLM tries to add are dropped."
        )
    )
    assessment: str = Field(description="Interpretation of observed facts")
    recommended_follow_ups: list[str] = Field(description="Actionable recommendations")
    risk_level: str = Field(description="informational|low|medium|high")
    confidence: str = Field(description="low|medium|high")
    events_analyzed: int = Field(description="Number of events included")
    model_used: str = Field(description="Perplexity model used")
    generated_at: datetime
