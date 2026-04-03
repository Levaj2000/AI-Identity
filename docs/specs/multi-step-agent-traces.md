# Multi-Step Agent Trace Support

| Field              | Value                                          |
|--------------------|------------------------------------------------|
| **Status**         | Planned                                        |
| **Priority**       | P1 -- High                                     |
| **Author**         | AI Identity Engineering                        |
| **Created**        | 2026-04-03                                     |
| **Target Release** | v0.9.0                                         |
| **Est. Effort**    | 6--8 engineering weeks across 4 phases         |
| **Depends On**     | Existing audit log HMAC chain, gateway enforce |
| **Stakeholders**   | Platform Engineering, Compliance, Product       |

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Proposed Solution: Trace Protocol](#2-proposed-solution-trace-protocol)
3. [Database Changes](#3-database-changes)
4. [Gateway Changes](#4-gateway-changes)
5. [API Changes](#5-api-changes)
6. [Dashboard Changes](#6-dashboard-changes)
7. [SDK / Client Integration](#7-sdk--client-integration)
8. [Policy Extensions (Future)](#8-policy-extensions-future)
9. [Migration Strategy](#9-migration-strategy)
10. [Open Questions](#10-open-questions)
11. [Appendix: Wire Examples](#appendix-wire-examples)

---

## 1. Problem Statement

Modern AI agents built on frameworks like LangChain, CrewAI, and AutoGen do not
execute a single request-response cycle. They orchestrate multi-step workflows
where the output of one LLM call feeds into the next: classify intent, retrieve
context, draft a response, self-critique, revise. A single user-facing action
may generate 3--15 gateway requests.

Today, the AI Identity gateway treats each request independently. The
`audit_log` table records individual entries with no way to link steps that
belong to the same workflow execution. This creates four concrete problems:

**1. Incident reconstruction is incomplete.** The Forensics `/reconstruct`
endpoint returns a flat list of events in a time window. An investigator cannot
distinguish which events belong to the same workflow, making root-cause analysis
guesswork when multiple workflows overlap in the same time range.

**2. Workflow graphs cannot be visualized.** Agent frameworks produce directed
acyclic graphs (DAGs) of execution -- tool calls that branch and converge. There
is no data model to reconstruct these graphs in the dashboard.

**3. Cost and latency attribution is per-request only.** Operators cannot answer
"how much did this entire workflow cost?" or "what is the end-to-end latency of
the classification pipeline?" without manual correlation.

**4. Policies cannot reason about workflow context.** The gateway evaluates each
request in isolation. It cannot enforce rules like "this agent may only call
GPT-4 during the final synthesis step" or "no workflow may exceed $0.50 total."

### Scope

This specification covers the trace data model, gateway header protocol, API
endpoints, dashboard views, and SDK integration patterns. Policy extensions that
depend on trace context are described at a high level but deferred to a future
specification.

---

## 2. Proposed Solution: Trace Protocol

Introduce four optional HTTP headers that agents attach to gateway requests.
Because all headers are optional, this is fully backwards-compatible -- agents
that do not send them continue to work identically.

### Header Definitions

| Header                | Type     | Required | Description |
|-----------------------|----------|----------|-------------|
| `X-Trace-Id`         | UUID v4  | No       | Unique identifier for the entire workflow execution. Generated once at the start of a workflow and reused on every step. |
| `X-Parent-Request-Id` | Integer | No       | The `audit_log.id` of the preceding step. Enables parent-child DAG construction. |
| `X-Step-Name`        | String   | No       | Human-readable label for this step (e.g., `classify-intent`, `draft-response`). Max 128 characters, alphanumeric + hyphens + underscores. |
| `X-Step-Index`       | Integer  | No       | Zero-based sequential position of this step within the trace. Informational; the canonical ordering is `created_at`. |

### Protocol Rules

1. If `X-Trace-Id` is present but `X-Parent-Request-Id` is absent, this step is
   the **root** of the trace.
2. If `X-Trace-Id` is absent, the request is treated as a standalone
   (single-step) entry. No trace metadata is stored.
3. The gateway returns the `audit_log.id` of the newly created entry in the
   response header `X-Request-Id`. The agent SDK uses this value as
   `X-Parent-Request-Id` on the subsequent step.
4. `X-Step-Name` and `X-Step-Index` are purely informational enrichment. They
   are stored but never used for enforcement logic in Phase 1--3.

### Trace Lifecycle

```
Agent SDK                          Gateway                         Audit Log
    |                                 |                                |
    |  POST /v1/chat                  |                                |
    |  X-Trace-Id: abc-123            |                                |
    |  X-Step-Name: classify-intent   |                                |
    |  X-Step-Index: 0                |                                |
    |-------------------------------->|                                |
    |                                 |  enforce() + write audit entry |
    |                                 |------------------------------->|
    |                                 |    audit_log.id = 42           |
    |                                 |<-------------------------------|
    |  200 OK                         |                                |
    |  X-Request-Id: 42               |                                |
    |<--------------------------------|                                |
    |                                 |                                |
    |  POST /v1/chat                  |                                |
    |  X-Trace-Id: abc-123            |                                |
    |  X-Parent-Request-Id: 42        |                                |
    |  X-Step-Name: draft-response    |                                |
    |  X-Step-Index: 1                |                                |
    |-------------------------------->|                                |
    |                                 |  enforce() + write audit entry |
    |                                 |------------------------------->|
    |                                 |    audit_log.id = 43           |
    |                                 |    parent_request_id = 42      |
    |                                 |<-------------------------------|
    |  200 OK                         |                                |
    |  X-Request-Id: 43               |                                |
    |<--------------------------------|                                |
```

### DAG Construction from Trace Data

For branching workflows (e.g., parallel tool calls), the parent-child
relationship forms a DAG:

```
                    [step 0: classify]
                     /              \
          [step 1: tool-a]    [step 2: tool-b]
                     \              /
                    [step 3: synthesize]

audit_log rows:
  id=42  trace_id=abc  parent_request_id=NULL   step_name=classify      step_index=0
  id=43  trace_id=abc  parent_request_id=42     step_name=tool-a        step_index=1
  id=44  trace_id=abc  parent_request_id=42     step_name=tool-b        step_index=2
  id=45  trace_id=abc  parent_request_id=43,44  step_name=synthesize    step_index=3
```

Note: `parent_request_id` is a single integer FK in the schema. For convergent
nodes (step 3 above), the agent passes the ID of the *last* parent to complete.
A supplementary `trace_parents` JSONB column (see Section 3, Future) can store
multiple parents for full DAG fidelity if needed.

---

## 3. Database Changes

### New Columns on `audit_log`

Add four nullable columns to the existing `audit_log` table. All are nullable
to maintain backwards compatibility -- existing rows and agents that do not send
trace headers will have `NULL` values.

```python
# common/models/audit_log.py -- additions

from sqlalchemy import ForeignKey

class AuditLog(Base):
    # ... existing columns ...

    # ── Trace metadata (NOT included in HMAC integrity chain) ──
    trace_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=False,  # covered by ix_audit_log_trace_id below
        comment="UUID linking all steps in a multi-step workflow",
    )
    parent_request_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("audit_log.id", ondelete="SET NULL"),
        nullable=True,
        comment="audit_log.id of the preceding step (self-referencing FK)",
    )
    step_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Human-readable step label (e.g. classify-intent)",
    )
    step_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Zero-based sequential position within the trace",
    )
```

### New Indexes

```python
    __table_args__ = (
        # ... existing indexes ...
        Index("ix_audit_log_trace_id", "trace_id"),
        Index("ix_audit_log_trace_created", "trace_id", "created_at"),
    )
```

The `ix_audit_log_trace_id` index supports fast retrieval of all steps in a
trace. The composite `ix_audit_log_trace_created` supports ordered trace
reconstruction without a filesort.

### HMAC Integrity Chain -- Exclusion

**These four columns are explicitly NOT included in the HMAC integrity chain.**

The `_canonical_payload()` function in `common/audit/writer.py` constructs the
hash input from security-critical fields: `agent_id`, `endpoint`, `method`,
`decision`, `cost_estimate_usd`, `latency_ms`, `request_metadata`, `created_at`,
and `prev_hash`. Trace metadata is enrichment data, not security-critical. It
follows the same pattern as `user_id` and `agent_name`, which are also excluded
from the hash.

This means:
- Trace columns can be backfilled or corrected without breaking the chain.
- Chain verification (`verify_chain()`) remains unchanged.
- SOC 2 integrity guarantees are unaffected.

### Alembic Migration

```
alembic/versions/l2g3h4i5j6k7_add_trace_columns.py
```

The migration adds all four columns as nullable with no default, then creates
the two indexes. This is a non-locking `ALTER TABLE ADD COLUMN` on PostgreSQL
for nullable columns with no default -- zero downtime.

### Future: Multi-Parent Support

For full DAG fidelity with convergent nodes, a future migration can add:

```python
    trace_parents: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of parent audit_log.ids for convergent DAG nodes",
    )
```

This is deferred because the single `parent_request_id` FK covers the common
case (linear chains and single-parent trees), and JSONB arrays complicate
referential integrity.

---

## 4. Gateway Changes

### Header Extraction in `enforce()`

Modify the `enforce()` function in `gateway/app/enforce.py` to accept optional
trace parameters and pass them through to the audit writer.

```python
def enforce(
    db: Session,
    *,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    key_type: str | None = None,
    request_metadata: dict | None = None,
    # ── New trace parameters ──
    trace_id: str | None = None,
    parent_request_id: int | None = None,
    step_name: str | None = None,
    step_index: int | None = None,
) -> EnforcementResult:
```

These parameters flow through `_audit_decision()` to `create_audit_entry()`.

### Header Extraction in `gateway/app/main.py`

The `/gateway/enforce` endpoint extracts trace headers from the incoming
request:

```python
@app.post("/gateway/enforce")
def enforce_request(
    request: Request,
    agent_id: uuid.UUID = Query(...),
    endpoint: str = Query(...),
    method: str = Query("POST"),
    key_type: str | None = Query(None),
    review_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    # Extract trace headers
    trace_id = request.headers.get("x-trace-id")
    parent_request_id_raw = request.headers.get("x-parent-request-id")
    parent_request_id = int(parent_request_id_raw) if parent_request_id_raw else None
    step_name = request.headers.get("x-step-name")
    step_index_raw = request.headers.get("x-step-index")
    step_index = int(step_index_raw) if step_index_raw else None

    # Validate trace_id format (UUID)
    if trace_id:
        try:
            uuid.UUID(trace_id)
        except ValueError:
            trace_id = None  # Silently ignore malformed trace IDs

    # Validate step_name (alphanumeric + hyphens + underscores, max 128)
    if step_name and (len(step_name) > 128 or not re.match(r'^[a-zA-Z0-9_-]+$', step_name)):
        step_name = None

    result = enforce(
        db,
        agent_id=agent_id,
        endpoint=endpoint,
        method=method,
        key_type=key_type,
        trace_id=trace_id,
        parent_request_id=parent_request_id,
        step_name=step_name,
        step_index=step_index,
    )
```

### Audit Entry ID in Response

The gateway already sets `X-Request-ID` in the response via the
`request_logging_middleware`. After enforcement, the response must also include
the `audit_log.id` so the agent can thread it as `X-Parent-Request-Id`:

```python
    # In enforce_request(), after audit entry creation:
    response["audit_entry_id"] = result.audit_entry_id  # new field on EnforcementResult

    # Also set as response header for agents that read headers:
    response_obj = JSONResponse(content=response)
    response_obj.headers["X-Request-Id"] = str(result.audit_entry_id)
    return response_obj
```

This requires `EnforcementResult` and `_audit_decision()` to capture and return
the `audit_log.id` from `create_audit_entry()`.

### Audit Writer Changes

Extend `create_audit_entry()` in `common/audit/writer.py` to accept and store
trace parameters:

```python
def create_audit_entry(
    db: Session,
    *,
    agent_id: uuid.UUID,
    endpoint: str,
    method: str,
    decision: str,
    cost_estimate_usd: float | None = None,
    latency_ms: int | None = None,
    request_metadata: dict | None = None,
    user_id: uuid.UUID | None = None,
    # ── New trace parameters ──
    trace_id: str | None = None,
    parent_request_id: int | None = None,
    step_name: str | None = None,
    step_index: int | None = None,
) -> AuditLog:
```

The trace parameters are set directly on the `AuditLog` instance but are NOT
passed to `_canonical_payload()` or `compute_entry_hash()`.

### Input Validation

| Header                | Validation                                                  | On failure       |
|-----------------------|-------------------------------------------------------------|------------------|
| `X-Trace-Id`         | Valid UUID v4 format                                        | Silently ignored |
| `X-Parent-Request-Id` | Positive integer; referenced row must exist in `audit_log` | Silently ignored |
| `X-Step-Name`        | 1--128 chars, `[a-zA-Z0-9_-]+`                             | Silently ignored |
| `X-Step-Index`       | Non-negative integer                                        | Silently ignored |

Invalid trace headers are silently dropped (not rejected). This ensures that a
misconfigured agent SDK does not break request processing. Invalid values are
logged at DEBUG level for troubleshooting.

---

## 5. API Changes

### New Endpoint: GET /api/v1/traces/{trace_id}

Returns all audit entries for a single trace, ordered by `created_at`, with
parent-child relationships resolved into a tree structure.

**Route:** `GET /api/v1/traces/{trace_id}`

**Auth:** Requires authenticated user. Results scoped to agents owned by the
user (same tenant isolation as existing audit endpoints).

**Path Parameters:**

| Param      | Type   | Description                  |
|------------|--------|------------------------------|
| `trace_id` | string | UUID of the trace to retrieve |

**Response Schema:**

```json
{
  "trace_id": "abc-123-...",
  "agent_id": "550e8400-...",
  "agent_name": "Customer Support Bot",
  "started_at": "2026-04-03T10:00:00Z",
  "ended_at": "2026-04-03T10:00:02.341Z",
  "duration_ms": 2341,
  "step_count": 4,
  "total_cost_usd": 0.0234,
  "decisions": {
    "allow": 3,
    "deny": 1,
    "error": 0
  },
  "steps": [
    {
      "id": 42,
      "parent_request_id": null,
      "step_name": "classify-intent",
      "step_index": 0,
      "endpoint": "/v1/chat/completions",
      "method": "POST",
      "decision": "allow",
      "cost_estimate_usd": 0.0052,
      "latency_ms": 340,
      "created_at": "2026-04-03T10:00:00Z",
      "request_metadata": { ... },
      "children": [43, 44]
    },
    ...
  ],
  "tree": {
    "id": 42,
    "children": [
      { "id": 43, "children": [{ "id": 45, "children": [] }] },
      { "id": 44, "children": [{ "id": 45, "children": [] }] }
    ]
  }
}
```

The `steps` array is a flat list ordered by `created_at`. The `tree` object is
a nested structure derived from `parent_request_id` relationships for rendering
the DAG view.

### New Endpoint: GET /api/v1/traces

Lists recent traces with summary statistics. This is the primary entry point
for the Trace View in the Forensics dashboard.

**Route:** `GET /api/v1/traces`

**Query Parameters:**

| Param        | Type     | Default | Description                              |
|--------------|----------|---------|------------------------------------------|
| `agent_id`   | UUID     | null    | Filter by agent                          |
| `start_date` | datetime | null    | Traces started after this timestamp      |
| `end_date`   | datetime | null    | Traces started before this timestamp     |
| `min_steps`  | int      | null    | Minimum step count (filter out singles)  |
| `decision`   | string   | null    | Only traces containing this decision     |
| `limit`      | int      | 50      | Pagination limit (1--500)                |
| `offset`     | int      | 0       | Pagination offset                        |

**Response Schema:**

```json
{
  "items": [
    {
      "trace_id": "abc-123-...",
      "agent_id": "550e8400-...",
      "agent_name": "Customer Support Bot",
      "started_at": "2026-04-03T10:00:00Z",
      "ended_at": "2026-04-03T10:00:02.341Z",
      "duration_ms": 2341,
      "step_count": 4,
      "total_cost_usd": 0.0234,
      "decisions": { "allow": 3, "deny": 1, "error": 0 },
      "root_step_name": "classify-intent",
      "has_denials": true
    }
  ],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

This endpoint uses a SQL aggregation query grouped by `trace_id`:

```sql
SELECT
    trace_id,
    MIN(agent_id)                                     AS agent_id,
    MIN(created_at)                                   AS started_at,
    MAX(created_at)                                   AS ended_at,
    EXTRACT(EPOCH FROM MAX(created_at) - MIN(created_at)) * 1000 AS duration_ms,
    COUNT(*)                                          AS step_count,
    COALESCE(SUM(cost_estimate_usd), 0)               AS total_cost_usd,
    COUNT(*) FILTER (WHERE decision = 'allow')        AS allow_count,
    COUNT(*) FILTER (WHERE decision = 'deny')         AS deny_count,
    COUNT(*) FILTER (WHERE decision = 'error')        AS error_count
FROM audit_log
WHERE trace_id IS NOT NULL
  AND agent_id IN (:user_agent_ids)
GROUP BY trace_id
ORDER BY MIN(created_at) DESC
LIMIT :limit OFFSET :offset;
```

### Extended: GET /api/v1/audit

Add `trace_id` as an optional filter parameter to the existing audit log list
endpoint:

```python
@router.get("")
def list_audit_logs(
    # ... existing params ...
    trace_id: str | None = Query(None, description="Filter by trace ID"),
):
```

When `trace_id` is provided, the query adds:
```python
query = query.filter(AuditLog.trace_id == trace_id)
```

### Pydantic Schemas

New schemas added to `common/schemas/agent.py`:

```python
class TraceStepResponse(BaseModel):
    """A single step within a trace."""
    id: int
    parent_request_id: int | None = None
    step_name: str | None = None
    step_index: int | None = None
    endpoint: str
    method: str
    decision: str
    cost_estimate_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime
    request_metadata: dict
    children: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TraceTreeNode(BaseModel):
    """Nested tree node for DAG rendering."""
    id: int
    step_name: str | None = None
    decision: str
    children: list["TraceTreeNode"] = Field(default_factory=list)


class TraceDetailResponse(BaseModel):
    """Full trace with all steps and tree structure."""
    trace_id: str
    agent_id: uuid.UUID
    agent_name: str | None = None
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    step_count: int
    total_cost_usd: float
    decisions: dict[str, int]
    steps: list[TraceStepResponse]
    tree: TraceTreeNode


class TraceSummaryResponse(BaseModel):
    """Summary of a trace for list views."""
    trace_id: str
    agent_id: uuid.UUID
    agent_name: str | None = None
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    step_count: int
    total_cost_usd: float
    decisions: dict[str, int]
    root_step_name: str | None = None
    has_denials: bool


class TraceListResponse(BaseModel):
    """Paginated list of trace summaries."""
    items: list[TraceSummaryResponse]
    total: int
    limit: int
    offset: int
```

---

## 6. Dashboard Changes

### 6.1 Forensics Page: Trace View Tab

Add a third view tab alongside the existing Timeline and Table views.

```
 [Timeline]  [Table]  [Traces]
                        ^^^^^^^
```

The Traces tab shows a list of traces grouped by `trace_id`, with each row
displaying:

```
+------------------------------------------------------------------+
| Trace abc-123...  |  4 steps  |  2.3s  |  $0.023  |  1 denial   |
| Customer Support Bot  |  classify -> draft -> review -> send     |
| Apr 3, 2026 10:00 AM                                             |
+------------------------------------------------------------------+
| Trace def-456...  |  2 steps  |  0.8s  |  $0.011  |  0 denials  |
| Data Pipeline Agent   |  fetch-data -> transform                 |
| Apr 3, 2026 09:45 AM                                             |
+------------------------------------------------------------------+
```

Each trace row is expandable inline or clickable to navigate to the Trace
Detail view.

### 6.2 Trace Detail View

A dedicated page at `/forensics/traces/{trace_id}` showing:

**Header:**
- Trace ID, agent name, total duration, total cost, step count
- Decision breakdown badges (3 allowed, 1 denied)

**Primary View: Connected Timeline**

For linear traces (no branching), render a vertical connected timeline:

```
    [1] classify-intent
     |  POST /v1/chat/completions
     |  ALLOW  |  340ms  |  $0.005
     |
    [2] retrieve-context
     |  POST /v1/embeddings
     |  ALLOW  |  120ms  |  $0.001
     |
    [3] draft-response
     |  POST /v1/chat/completions
     |  ALLOW  |  1,200ms  |  $0.015
     |
    [4] send-to-user
     |  POST /v1/chat/completions
     |  DENY (policy_denied)  |  --  |  --
```

**Alternate View: DAG**

For branching traces, render an interactive DAG with nodes and directed edges.
Nodes show step name, decision (color-coded: green=allow, red=deny,
yellow=error), and latency. Edges show parent-child relationships.

```
              +------------------+
              | classify-intent  |
              | ALLOW | 340ms    |
              +--------+---------+
                      / \
         +-----------+   +----------+
         | tool-a    |   | tool-b   |
         | ALLOW     |   | ALLOW    |
         | 450ms     |   | 380ms    |
         +-----+-----+   +----+----+
                \             /
              +--+------------+--+
              | synthesize       |
              | ALLOW | 1,200ms  |
              +------------------+
```

**Step Detail Panel:**

Clicking a step node opens a side panel with:
- Full audit log entry (all fields from `AuditLogResponse`)
- `request_metadata` rendered as a formatted JSON tree
- `entry_hash` and `prev_hash` for chain verification
- Link to adjacent steps (parent / children)

### 6.3 Shadow Agents Page

If a shadow agent has entries with `trace_id` values, group them by trace in
the Shadow Agents detail view. This helps operators understand whether a
shadow agent is executing coordinated multi-step workflows (higher risk) versus
isolated one-off requests.

### 6.4 Compliance Page

Add trace-level compliance assessment:

- **Trace violation flag:** If any step in a trace has `decision=deny`, the
  entire trace is flagged as containing a policy violation.
- **Trace compliance summary:** For a given time window, show:
  - Total traces
  - Traces with zero violations
  - Traces with at least one violation
  - Violation rate (percentage of traces with denials)
- **Drill-down:** Click a flagged trace to jump to the Trace Detail view.

---

## 7. SDK / Client Integration

### 7.1 Python Helper Library

Provide a lightweight context manager that handles trace lifecycle:

```python
# ai_identity/trace.py

import uuid
from contextlib import contextmanager
from threading import local

_thread_local = local()


def _get_trace_state():
    if not hasattr(_thread_local, "trace_stack"):
        _thread_local.trace_stack = []
    return _thread_local.trace_stack


@contextmanager
def trace_context(name: str = ""):
    """Context manager for multi-step agent traces.

    Usage:
        from ai_identity import trace_context

        with trace_context("customer-support-workflow"):
            # All gateway requests inside this block share the same trace_id.
            # The SDK automatically threads X-Parent-Request-Id between steps.
            response1 = client.chat(...)
            response2 = client.chat(...)
    """
    state = _get_trace_state()
    trace_id = str(uuid.uuid4())
    state.append({
        "trace_id": trace_id,
        "name": name,
        "last_request_id": None,
        "step_index": 0,
    })
    try:
        yield trace_id
    finally:
        state.pop()


def get_trace_headers(step_name: str = "") -> dict[str, str]:
    """Return trace headers for the current context.

    Called by the AI Identity HTTP client before each gateway request.
    Returns an empty dict if no trace context is active.
    """
    state = _get_trace_state()
    if not state:
        return {}

    ctx = state[-1]
    headers = {"X-Trace-Id": ctx["trace_id"]}

    if ctx["last_request_id"] is not None:
        headers["X-Parent-Request-Id"] = str(ctx["last_request_id"])

    effective_name = step_name or ctx.get("name", "")
    if effective_name:
        headers["X-Step-Name"] = effective_name

    headers["X-Step-Index"] = str(ctx["step_index"])
    return headers


def record_request_id(request_id: int):
    """Record the audit entry ID returned by the gateway.

    Called after each gateway response to thread the parent ID.
    """
    state = _get_trace_state()
    if state:
        state[-1]["last_request_id"] = request_id
        state[-1]["step_index"] += 1
```

### 7.2 Framework Integration Guides

#### LangChain

```python
from langchain.callbacks.base import BaseCallbackHandler
from ai_identity import trace_context, get_trace_headers, record_request_id


class AIIdentityTraceCallback(BaseCallbackHandler):
    """LangChain callback that auto-generates trace context."""

    def on_chain_start(self, serialized, inputs, **kwargs):
        chain_name = serialized.get("name", "langchain-chain")
        self._ctx = trace_context(chain_name)
        self._ctx.__enter__()

    def on_chain_end(self, outputs, **kwargs):
        self._ctx.__exit__(None, None, None)

    def on_llm_start(self, serialized, prompts, **kwargs):
        # Headers are injected by the AI Identity HTTP client
        pass
```

#### CrewAI

```python
from crewai import Task
from ai_identity import trace_context

# CrewAI task callback integration
with trace_context("crew-research-task"):
    result = crew.kickoff()
    # All LLM calls within the crew execution share the trace_id
```

#### AutoGen

```python
from autogen import AssistantAgent
from ai_identity import trace_context

with trace_context("autogen-conversation"):
    assistant.initiate_chat(user_proxy, message="Analyze this data...")
    # Each message in the conversation is a step in the trace
```

#### OpenAI SDK (Direct)

```python
import openai
from ai_identity import get_trace_headers, record_request_id, trace_context

client = openai.OpenAI(
    base_url="https://gateway.ai-identity.co/v1",
    api_key="aid_sk_...",
)

with trace_context("my-workflow"):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[...],
        extra_headers=get_trace_headers("classify-intent"),
    )
    # Extract audit entry ID from response headers
    audit_id = int(response.headers.get("x-request-id", 0))
    record_request_id(audit_id)
```

---

## 8. Policy Extensions (Future)

These extensions depend on trace context being available in the gateway at
enforcement time. They are described here for completeness but are out of scope
for the initial implementation (Phases 1--3).

### 8.1 Step-Scoped Policies

Allow policy rules to constrain behavior by step name:

```json
{
  "allowed_endpoints": ["/v1/chat/*"],
  "step_rules": {
    "classify-intent": {
      "allowed_models": ["gpt-3.5-turbo"],
      "max_cost_usd": 0.01
    },
    "final-synthesis": {
      "allowed_models": ["gpt-4", "gpt-4-turbo"],
      "max_cost_usd": 0.10
    }
  }
}
```

The gateway would match `X-Step-Name` against `step_rules` keys and apply the
scoped constraints in addition to the base policy.

### 8.2 Trace-Level Budgets

Enforce cumulative cost limits across all steps in a trace:

```json
{
  "trace_budget": {
    "max_cost_usd": 0.50,
    "max_steps": 15,
    "max_duration_seconds": 30
  }
}
```

Implementation requires the gateway to query aggregate cost for the trace
before allowing each step. This adds a read query per enforcement, so it must
be evaluated for latency impact.

### 8.3 Branching Limits

Prevent infinite loops and runaway agents:

```json
{
  "trace_limits": {
    "max_steps": 10,
    "max_depth": 5,
    "max_concurrent_branches": 3
  }
}
```

The gateway checks the current step count for the trace and denies if limits
are exceeded. This is a simple `COUNT(*) WHERE trace_id = :trace_id` before
enforcement.

---

## 9. Migration Strategy

### Phase 1: Data Model + Gateway Extraction (2 weeks)

**Goal:** Capture trace data without requiring any client changes.

- Alembic migration: add `trace_id`, `parent_request_id`, `step_name`,
  `step_index` columns to `audit_log`
- Create `ix_audit_log_trace_id` and `ix_audit_log_trace_created` indexes
- Extend `create_audit_entry()` to accept and store trace parameters
- Extend `enforce()` to accept trace parameters
- Extract trace headers in `gateway/app/main.py` and pass to `enforce()`
- Return `audit_log.id` in `X-Request-Id` response header
- Add `trace_id` filter to existing `GET /api/v1/audit` endpoint
- Tests: unit tests for header extraction, audit entry creation with trace
  fields, backwards compatibility (no headers = NULL fields)

**Backwards compatibility:** Fully backwards-compatible. No client changes
needed. Agents that do not send trace headers see no change in behavior.

### Phase 2: API Endpoints + Forensics Trace View (2--3 weeks)

**Goal:** Expose trace data through the API and basic dashboard UI.

- Implement `GET /api/v1/traces` (list with aggregation)
- Implement `GET /api/v1/traces/{trace_id}` (detail with tree construction)
- Pydantic schemas for trace responses
- Forensics page: Trace View tab (list of traces)
- Trace Detail view (connected timeline + DAG visualization)
- Compliance page: trace-level violation summary
- Tests: API endpoint tests, tree construction from parent_request_id,
  aggregation query correctness

### Phase 3: SDK Helpers + Documentation (1--2 weeks)

**Goal:** Make it easy for agent developers to instrument traces.

- Publish `ai_identity.trace` Python module (trace_context, get_trace_headers,
  record_request_id)
- Framework integration guides (LangChain, CrewAI, AutoGen, OpenAI SDK)
- API documentation updates
- Dashboard tooltip/help text explaining trace concepts
- Example notebooks demonstrating traced workflows

### Phase 4: Policy Extensions (Future -- not scheduled)

**Goal:** Enable trace-aware policy enforcement.

- Step-scoped policies
- Trace-level budgets
- Branching limits
- Policy validator updates for new rule keys
- Requires separate specification and review

---

## 10. Open Questions

### Q1: Should `trace_id` be enforced unique per tenant, or globally?

**Recommendation:** Globally unique. UUIDs have negligible collision probability
and global uniqueness simplifies the data model (no composite key needed). The
`ix_audit_log_trace_id` index does not need a tenant prefix.

**Consideration:** If two tenants accidentally use the same trace_id (extremely
unlikely with UUID v4), tenant isolation is preserved by the existing
`agent_id IN (:user_agent_ids)` filter on all queries.

### Q2: Should the gateway auto-generate a `trace_id` if none is provided?

**Recommendation:** No, not in Phase 1. Auto-generating trace IDs for every
request would create millions of single-step "traces" that add noise without
value. Traces should be opt-in, representing intentional multi-step workflows.

**Revisit in Phase 4:** If policy extensions need trace context for all
requests (e.g., per-request cost tracking), auto-generation can be added as a
tenant-level configuration option.

### Q3: How do we handle traces that span multiple agents?

**Scenario:** Agent A (orchestrator) calls Agent B (specialist) as a tool. Both
agents go through the gateway with different `agent_id` values but should be
part of the same trace.

**Recommendation:** Allow it. `trace_id` is not constrained to a single
`agent_id`. The `GET /api/v1/traces/{trace_id}` endpoint returns steps from
all agents the user owns. The trace summary shows the primary (root) agent,
and the step list shows each step's agent.

**Consideration:** Cross-tenant traces (Agent A owned by User 1 calls Agent B
owned by User 2) are not supported. Each user sees only their own agent's steps
within the shared trace_id. This is a natural consequence of existing tenant
isolation.

### Q4: Should traces have a different retention policy than individual entries?

**Recommendation:** No special retention in Phase 1. Trace metadata lives on
the `audit_log` rows, so it follows the same retention policy. If a future
retention feature deletes old audit entries, the trace is naturally
deconstructed.

**Consideration:** A future "trace archive" feature could snapshot completed
traces as a single JSON document in cold storage before individual entries are
purged, preserving the workflow graph for long-term compliance.

### Q5: What happens if `X-Parent-Request-Id` references a non-existent entry?

**Recommendation:** Store it anyway. The FK constraint uses `ON DELETE SET NULL`,
so if the parent is ever deleted, the reference becomes NULL. If the referenced
ID never existed (agent error), the column still stores the value. The tree
construction algorithm in the API treats orphaned `parent_request_id` values as
additional root nodes within the trace.

### Q6: Performance impact of trace aggregation queries?

The `GET /api/v1/traces` endpoint runs a `GROUP BY trace_id` aggregation. With
the `ix_audit_log_trace_created` index, PostgreSQL can perform an index-only
scan for the grouping and use a bitmap heap scan for the aggregates.

**Estimated impact:** For a tenant with 100K audit entries and 10K distinct
traces, the aggregation query should complete in <50ms with the composite index.
Monitor query performance after Phase 2 launch and add materialized views if
needed.

---

## Appendix: Wire Examples

### Example: Traced Request (Root Step)

```http
POST /gateway/enforce?agent_id=550e8400-...&endpoint=/v1/chat/completions&method=POST HTTP/1.1
Host: gateway.ai-identity.co
Authorization: Bearer aid_sk_...
X-Trace-Id: 7f3a9b2c-1d4e-5f6a-8b7c-9d0e1f2a3b4c
X-Step-Name: classify-intent
X-Step-Index: 0
```

```http
HTTP/1.1 200 OK
X-Request-Id: 42
Content-Type: application/json

{
  "decision": "allow",
  "status_code": 200,
  "message": "Request allowed",
  "audit_entry_id": 42
}
```

### Example: Traced Request (Child Step)

```http
POST /gateway/enforce?agent_id=550e8400-...&endpoint=/v1/chat/completions&method=POST HTTP/1.1
Host: gateway.ai-identity.co
Authorization: Bearer aid_sk_...
X-Trace-Id: 7f3a9b2c-1d4e-5f6a-8b7c-9d0e1f2a3b4c
X-Parent-Request-Id: 42
X-Step-Name: draft-response
X-Step-Index: 1
```

```http
HTTP/1.1 200 OK
X-Request-Id: 43
Content-Type: application/json

{
  "decision": "allow",
  "status_code": 200,
  "message": "Request allowed",
  "audit_entry_id": 43
}
```

### Example: Untraced Request (Backwards Compatible)

```http
POST /gateway/enforce?agent_id=550e8400-...&endpoint=/v1/chat/completions&method=POST HTTP/1.1
Host: gateway.ai-identity.co
Authorization: Bearer aid_sk_...
```

```http
HTTP/1.1 200 OK
X-Request-Id: 44
Content-Type: application/json

{
  "decision": "allow",
  "status_code": 200,
  "message": "Request allowed",
  "audit_entry_id": 44
}
```

No trace headers sent, no trace metadata stored. `audit_log.trace_id` is NULL.
Behavior is identical to today.
