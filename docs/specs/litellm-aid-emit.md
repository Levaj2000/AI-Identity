# LiteLLM adapter for AID-EMIT-1: callback outline

| Field | Value |
|---|---|
| **Status** | Draft outline, design only. Nothing built. |
| **Proposed home** | `integrations/litellm-aid-emit/`, not yet created (import `aid_litellm`) |
| **Depends on** | `aid-emit` (see [`aid-emit-py.md`](aid-emit-py.md)); LiteLLM proxy pinned to one exact version, chosen in step 0 |
| **Platform side** | Existing edge registration (`POST /api/v1/edges`) and `POST /api/v1/audit/ingest`. One platform change for phase 1: ingest reads stream stamps from `aid.stream` as well as `cpex.stream` |
| **Sequencing** | Phase 1 can be built now. Phase 3 enforces against the AI Identity mandate service directly; no dependency on Praxis or CPEX. |
| **Vocabulary** | AI Identity and OCSF: native OCSF fields first, AI Identity `aid.*` names under `unmapped` for the gaps ([`aid-emit-py.md`](aid-emit-py.md) section 4.1) |
| **Date** | 2026-10-12 |

Hook names and signatures below come from LiteLLM's `CustomLogger` interface as
documented. They are **not yet verified against a pinned version**. Step 0 of
the build plan does that, and its result decides sections 4 and 5.

---

## 1. What a record claims, and what it does not

A record from this adapter claims:

> LiteLLM proxy instance E, holding signing key K, saw request R from
> principal P **as LiteLLM authenticated P**, for model group G. The request
> was ruled V, routed to deployment D, and ended with outcome O, with the token
> counts and cost LiteLLM computed.

It does **not** claim:

- that the model ran, or produced the output (the proxy saw a response, not an
  execution);
- an agent identity, unless a mandate Biscuit verified (phases 2 and 3). A
  LiteLLM virtual key names a tenant, not an agent;
- anything about content. No prompts or responses; at most keyed digests
  (section 7).

Keep public copy inside this boundary. An auditor will compare the claim with
the signer.

## 2. Phases

| Phase | Behavior | Blocks requests? | Needs |
|---|---|---|---|
| **P1 Observe** | One signed decision record per request, at its terminal outcome. Identity as LiteLLM saw it. | Never | `aid-emit`, an edge registration |
| **P2 Shadow** | Also verify `X-Agent-Mandate` offline against the root public key. `ai_agent` / `delegation` come only from a token that verified. A would-deny is recorded as step `deny_ignored` with `detail.code`. | Never | Offline Biscuit verification against the published root public key |
| **P3 Enforce** | A pre-call guard denies on mandate failure and settles the draw with the mandate service; the join key equals the receipt's `correlation_id`. | Yes, fail-closed | Spend semantics decided (open question 4) |

P2 is shadow mode: run the check, record what it would have done, never act. For an edge in front of a model it is the
lowest-risk way to show a customer what enforcement would catch.

## 3. Components

Two classes, keeping enforcement and evidence apart:

- `AIDEvidenceLogger(CustomLogger)`: observation-only. Builds and emits
  records. Never raises into LiteLLM (AID-EMIT-1 section 10).
- `AIDMandateGuard` (phase 2 onward): verifies the Biscuit in the pre-call hook.
  P2 records the outcome; P3 raises to deny. Its fail-closed rule belongs to
  it, never to the logger.

Wiring (P1):

```yaml
litellm_settings:
  callbacks: aid_litellm.handler.evidence_logger
```

Run with one worker for the POC (`--num_workers 1`). One chain per process is
a hard rule; see [`aid-emit-py.md`](aid-emit-py.md) section 7.

## 4. Hooks and exactly-once emission

| Hook | Used for |
|---|---|
| `async_pre_call_hook(user_api_key_dict, cache, data, call_type)` | Register `pending[call_id]` with start time and principal. P2/P3: run the guard and store its step there. |
| `async_log_success_event(kwargs, response_obj, start_time, end_time)` | Terminal record for success. Read `kwargs["standard_logging_object"]` for deployment, tokens and cost. |
| `async_post_call_failure_hook(request_data, original_exception, user_api_key_dict, traceback_str)` | Terminal record for every failure: auth, budget, rate limit, guardrail, our deny, upstream error. |
| `async_log_failure_event` | Not an emission point, to avoid emitting twice. Used only if step 0 shows it carries deployment detail the failure hook lacks. |

Rules:

- **Key** is `litellm_call_id`. A per-process `emitted` set with a TTL ensures
  at most one terminal record per call id, whichever hook fires first.
- **Failures without a pending entry are still emitted.** Auth rejections
  happen before the pre-call hook, and they are exactly the denials a
  post-hook observer never sees (AID-EMIT-1 section 9.3).
- **Abandoned requests are emitted too.** A sweeper emits a record for any
  `pending` entry older than the request timeout plus a margin, with
  `status_code: no_terminal_event`. Otherwise a client disconnect, or a hook
  LiteLLM skipped, is a request with no evidence and nothing showing the gap.
- **Streaming:** the success record is emitted when the stream completes. Step
  0 confirms what fires on a mid-stream provider error and on a client
  disconnect mid-stream.
- **Retries and fallbacks:** one call id, one record, for the final outcome.
  The deployments attempted go in `unmapped."aid.litellm.routing".attempts` if
  step 0 shows LiteLLM exposes them.

## 5. Verdict mapping (AID-EMIT-1 section 9.1)

The distinction that matters: **a provider failure is not a denial, and a
denial is not an error.** It is the same distinction section 9.2 draws between
`aborted` and `error`.

| Outcome | `action_id` | `disposition_id` | `status_id` | `status_code` | Step action |
|---|---|---|---|---|---|
| Success | 1 Allowed | 1 Allowed | 1 Success | (none) | `allowed` |
| Proxy auth rejected | 2 Denied | 2 Blocked | 2 Failure | `auth_rejected` | `denied` |
| Budget exceeded | 2 Denied | 2 Blocked | 2 Failure | `budget_exceeded` | `denied` |
| Proxy rate limit | 2 Denied | 2 Blocked | 2 Failure | `rate_limited` | `denied` |
| Guardrail blocked | 2 Denied | 2 Blocked | 2 Failure | `guardrail_blocked` | `denied` |
| Mandate denied (P3) | 2 Denied | 2 Blocked | 2 Failure | `mandate_exceeded` / `mandate_invalid` | `denied` (plugin `aid-mandate`) |
| Mandate would deny (P2) | per real outcome | per real outcome | per real outcome | per real outcome | `deny_ignored`, plus flat `deny_ignored: true` |
| Upstream provider error | 1 Allowed | 1 Allowed | 2 Failure | `upstream_error` | `allowed`, then outcome error |
| Upstream timeout | 1 Allowed | 1 Allowed | 2 Failure | `upstream_timeout` | as above |
| No terminal hook fired | 0 Unknown | 0 Unknown | 0 Unknown | `no_terminal_event` | (none) |
| Unclassified exception | 0 Unknown | 0 Unknown | 2 Failure | `unclassified:<ExceptionClass>` | `error` |

- Classification is keyed on exception class and origin (proxy vs provider),
  using the matrix from step 0. The default for anything unrecognized is
  Unknown. It is **never** Allowed or Denied by default.
- `0 Unknown` goes beyond section 9.1's three verdicts. See open question 2.
- **Modified-allow:** P1 cannot detect that a LiteLLM guardrail rewrote the
  request (masking, PII redaction), so it would record a plain allow.
  AID-EMIT-1 says a modified-allow MUST NOT be recorded as a plain allow. So
  P1 is conformant **only with mutating guardrails off**, and the adapter
  refuses to start, with a clear message, if it finds one configured. See open
  question 5.

Steps (`unmapped."aid.decision".steps`): P1 emits one step,
`{"plugin": "litellm-proxy", "phase": "sequential", "action": ..., "detail": {"code", "reason"}}`.
P2 and P3 put the `aid-mandate` step first.

## 6. Field mapping

| OCSF / AID-EMIT-1 field | Source | Notes |
|---|---|---|
| `class_uid` 6003, `category_uid` 6, `activity_id` 99, `type_uid` 600399 | constant | |
| `activity_name` | `"Completion"` for completion and responses call types | Other call types: open question 1 |
| `time` | `start_time` | RFC 3339, milliseconds, `Z` |
| `duration` | `end_time - start_time` | integer ms |
| `metadata.profiles` | `ai_operation`, `security_control`, plus `record_integrity` (library) | |
| `metadata.correlation_uid` | `X-AI-Identity-Run-Id` header, else LiteLLM session/trace id | Run-stable id. A correlation hint, not an authenticated claim |
| `api.request.uid` | `litellm_call_id` | Per-call id |
| `unmapped."aid.request_id"` | `litellm_call_id` | The join key (section 8). P3 passes the same value as `X-Correlation-ID` when settling, so the receipt reconciles. Set from P1 so the key never changes shape |
| `actor.user.uid` | `user_api_key_dict.user_id` | The LiteLLM principal |
| `unmapped."aid.litellm.key"` | key alias, team id, org id, first 12 hex chars of the stored token hash | Never the key itself |
| `ai_model.name` | `standard_logging_object.model_group` | What was requested |
| `unmapped."aid.litellm.deployment"` | `model_id`, provider model string, `custom_llm_provider`, api_base **host only**, region from `model_info` if configured | What served it. The region is the data-residency evidence |
| `message_context` | prompt, completion and total tokens | integers |
| `unmapped."aid.litellm.cost"` | `{"cost_micros": round(response_cost * 1e6), "currency": "USD"}` | `response_cost` is a float, and floats are outside the section 4 value space. Integer micro-USD keeps it signable |
| `ai_agent`, `delegation` | **verified** Biscuit only (P2+) | Absent in P1. Never taken from an unverified header |
| `unmapped."aid.span"` | W3C `traceparent` if present | Optional |
| `unmapped."aid.stream"`, `attestation_list`, signature fields | `aid-emit` | The adapter never sets these |

## 7. Security requirements

1. **Decision state stays on the server.** The guard hands its step to the
   logger through the per-process `pending` map keyed by call id. It never
   goes through request `metadata`: LiteLLM merges client-supplied `metadata`
   from the request body, so an agent, or a prompt injection steering one,
   could write its own `allowed` step into signed evidence. The logger reads
   no decision field from anything the client can set.
2. **The mandate token never goes upstream.** A Biscuit is a bearer credential
   for its attenuated scope. Confirm that client-header forwarding to the
   provider is off, or that `X-Agent-Mandate` is stripped explicitly, and test
   it.
3. **No content in records.** If content provenance is wanted later, use the
   keyed form `hmac-sha256:<key_id>:<hex>` under a deployment secret
   (AID-EMIT-1 section 9.2). Never use unkeyed digests: a digest of short or
   templated prompt content lets anyone with a guess confirm what was asked.
4. **The logger is observation-only.** Every emitter call is wrapped in
   try/except, counted (`aid_litellm_emit_failures_total`), and swallowed. Only
   the P3 guard may fail a request.
5. **Key handling.** The signing key and the ingest key are mounted files
   (from a secret store), never env vars or `config.yaml`. One
   signing key per edge. In P1 the LiteLLM process can read the signing key;
   that is an accepted POC risk, which the production sidecar removes.
6. **Pin LiteLLM exactly, with hashes.** The proxy sits on the provider
   credential path, and this adapter runs inside it. Bump it deliberately, and
   re-run the step 0 matrix on each bump.

## 8. POC deployment

- docker-compose with LiteLLM (one worker, adapter installed in the image), a
  spool volume, and a mock OpenAI-compatible upstream with configurable
  latency, 5xx and timeouts, so no paid model is needed.
- Register the edge once:
  `POST /api/v1/edges {name, chain_uid, authority_uid, verify_key_pem, key_id}`
  returns the show-once `aid_edge_...` ingest key, which goes into a mounted
  file.
- The shipper runs as a thread in the LiteLLM process (in-process shape).

## 9. Build plan (phase 1, about a week)

| Step | Work | Est. |
|---|---|---|
| 0 | **Spike.** Pin LiteLLM. For each of: success, streaming success, auth reject, budget, proxy rate limit, guardrail block, provider 5xx, timeout, client disconnect mid-stream, fallback to a second deployment, record which hooks fire, in what order, how many times, and which fields are populated. Commit the matrix as `HOOK-MATRIX.md`. | 0.5 d |
| 1 | `aid-emit` core with tests T1 to T6. | 2 d |
| 2 | `AIDEvidenceLogger`: pending map, exactly-once, sweeper, verdict classifier from the step 0 matrix, field mapping. | 1.5 d |
| 3 | Compose demo, edge registration, ingest round trip (T7). | 1 d |
| 4 | CI: validator `--strict-gaps` and ingest assertions on the demo output. | 0.5 d |

**Acceptance for P1:**

- A run of N requests across every row of the step 0 matrix yields exactly N
  records: no duplicates, and no request missing a record.
- `aid_emit1_validator.py --strict-gaps` is clean, and ingest reports every
  record `verified`, with zero anomalies.
- `kill -9` mid-run, then restart. Result: exactly one epoch boundary, no
  duplicate uids, and anomalies only where a record was actually lost. This
  check needs a consumer that dedupes only identical replays; see
  [`aid-emit-py.md`](aid-emit-py.md) section 11, finding 1.

## 10. Decisions

- **Vocabulary (decided 2026-10-12).** This adapter targets the AI Identity
  platform and OCSF, not CPEX or Praxis. Native OCSF fields first; facts with
  no native home use the AI Identity `aid.*` names under `unmapped`. AID-EMIT-1
  absorbs this as a 1.2.0 vocabulary profile (additive, MINOR) rather than a
  new AID-EMIT-2, because the signing, chain and stream rules do not change.
  Two consumers must accept `aid.stream` before phase 1 ships: the ingest
  endpoint and `scripts/aid_emit1_validator.py`.
- **LiteLLM as a dependency (decided 2026-10-12).** Yes, for phase 1.

## 11. Open questions

1. **Activity names** for embedding, image, audio and rerank calls. Either
   emit `activity_id 99` with source-defined names, which extends the section 3
   mapping, or keep P1 to completions and record other call types as
   unsupported.
2. **Unknown verdict.** `action_id 0` / `disposition_id 0` for
   `no_terminal_event` and unclassified exceptions goes beyond section 9.1. The
   alternative is forcing every outcome into Allow or Deny, which would be a
   false claim.
3. **Multiple replicas.** One chain per pod means one edge registration per
   pod. Options: (a) a StatefulSet with pre-registered ordinal names; (b)
   ingest accepts several chains under one edge registration (a contained
   change to the ingest endpoint and its edge model). (b) is
   the better product answer once there is a real multi-replica customer.
4. **Spend semantics for P3.** Inference cost is known only after the call.
   Either pre-authorize an estimate (`max_tokens` x price) and settle the
   actual cost, or settle the actual cost after the call and accept a one-call
   overshoot of the ceiling. Settling a caller-declared amount before
   forwarding, which works for priced tool calls, does not carry over directly.
5. **Mutating guardrails.** Refuse to start (as proposed), or detect
   modification by digesting the request at entry and after the pre-call hooks.
   That depends on hook ordering, which step 0 has to establish.
