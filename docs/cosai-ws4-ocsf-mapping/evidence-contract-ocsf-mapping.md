# Evidence Contract → OCSF Mapping (CoSAI WS4)

**Deliverable for [cosai-oasis/ws4-secure-design-agentic-systems#172](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/172) Q14 · Pinned to OCSF v1.9.0 · Schema facts verified 2026-08-25**

The evidence contract under discussion in WS4 #172 — @imran-siddique's field list plus
@skvcool-rgb's two additions — mapped to where each field lands in OCSF, with the gaps named and
the issue tracking each gap referenced. Every schema claim below was verified against the
[`v1.9.0` tag](https://github.com/ocsf/ocsf-schema/tree/v1.9.0) of `ocsf/ocsf-schema` on the date
above (release 2026-08-03), not recalled from notes; where `main` (`1.10.0-dev`) was also checked,
the objects cited are identical unless noted.

Two scope notes up front:

- **This is the evidence half only.** Detection ("what to log so an escape attempt is
  detectable") and evidence ("what lets a failure be reconstructed by someone who wasn't there
  and doesn't trust you") are different artifacts optimised for different consumers. This
  document is the evidence contract mapping; the detection table is separate follow-on work.
  Concretely: this supplies the concrete logging schema WS4 #172 **Q14** asks for. Q14's other
  half — whether that schema belongs in the follow-on paper or in a playbook alongside the
  runtime-isolation guide — is a WG placement call this document does not make. It does **not**
  answer **Q15**, the false-positive profile for normal agent behaviour and what cross-run
  correlation requires operationally: that needs detection-side baselines this document has no
  data for, and is unclaimed at the time of writing.
- **Structure-independent.** WS4 #172 Q1 (bounded-authority decomposition vs. sandboxing frame)
  is unsettled. This mapping doesn't depend on the outcome — it slots into either structure.

**Wire evidence:** the "on the wire" column cites
[`ocsf-log-reference-bundle/`](./ocsf-log-reference-bundle/) — real exports from a running
gateway (`class_uid` 6003 under `ai_operation` + `record_integrity`, `metadata.version` 1.9.0,
per-event ECDSA-P256 signatures verifiable against a published JWKS). The mapping is checkable
against wire output, not prose — including where our own wire output falls short of the mapping
(§ Producer gaps).

---

## The contract

From WS4 #172 (§8 discussion). The evidence contract should connect, on every event:

1. the principal and delegation chain,
2. policy and tool-catalog versions,
3. the action or tool-call identifier,
4. a request digest,
5. the enforcement decision and reason,
6. runtime identity or attestation reference where available,
7. the outcome,
8. an integrity-protected sequence or timestamp.

Plus (@skvcool-rgb): (9) the principal **plus full delegation lineage** as the
integrity-protected correlation key on every event, and (10) the **accounting decision itself** —
aggregate consumed / remaining against the principal's budget — so enforcement is reconstructable,
not only the per-action decision.

## The mapping

| # | Contract field | OCSF home (v1.9.0) | Status | Issues | On the wire (reference bundle) |
|---|---|---|---|---|---|
| 1 | Principal | `actor` (`user`, `iam_role`, …) | Core | — | ✔ every event |
| 2 | Delegation (immediate) | `delegation` via the `ai_operation` profile — `uid` (required), `issuer_uid` (recommended), `parent_uid` (optional), `created_time` | v1.9.0 | [ocsf#1739](https://github.com/ocsf/ocsf-schema/issues/1739) for what's still missing | ✘ not yet emitted (P1) |
| 9 | Delegation lineage as correlation key | Single edge only: each event carries `uid` + optional `parent_uid`. Subtree reconstruction is a recursive walk over records a consumer may not hold | **Gap** | [ocsf#1739](https://github.com/ocsf/ocsf-schema/issues/1739) — `parent_uid` requirement + a materialised root identifier | ✘ |
| 2a | Policy version | `policy.version` (plus `policy.uid`, `policy.is_applied`) via the `security_control` profile, attached at `base_event` | v1.9.0 | — | ✘ `unmapped.policy_version` only (P2) |
| 2b | Tool-catalog version | None | **Missing** | [ocsf#1724](https://github.com/ocsf/ocsf-schema/issues/1724) — declared-configuration inventory | ✘ |
| 3 | Action / tool-call identifier | Transport level: `api.operation`, `api.request.uid`. Capability level (which tool, which server, request/result correlator): none | **Missing** | [ocsf#1728](https://github.com/ocsf/ocsf-schema/issues/1728) — `ai_tool` object | ◐ `api` present; capability identity in vendor fields |
| 4 | Request digest | `raw_data_hash` (type `fingerprint`) on `base_event`; `fingerprint` carries `algorithm`, `encoding_id`, `serialization`/`serialization_id` | v1.9.0 | — | ◐ content hashes inside the signed bytes; `raw_data_hash` itself not emitted (P3) |
| 5a | Enforcement decision | `action`/`action_id`, `disposition`/`disposition_id` via `security_control` | v1.9.0 | — | ✔ `action_id` 1/2 on every event (excerpt seq 16–22) |
| 5b | Enforcement reason | `status_code` / `status_detail` on `base_event` | Core | — | ✘ not populated on denials (P4) |
| 6 | Runtime identity / attestation reference | Instance: `ai_agent.instance_uid` (+ `uid`, `version`, `charter`). What actually ran (image/adapter digests): none | Partial | [ocsf#1724](https://github.com/ocsf/ocsf-schema/issues/1724) — `agent_artifact.fingerprint` (proposed) | ◐ `ai_agent` ✔; artifact digests ✘ |
| 7 | Outcome | `status` / `status_id` on `base_event` | Core | — | ✘ absent (allowed implied by `action_id`; see P5) |
| 8 | Integrity-protected sequence + timestamp | `attestation` via `record_integrity` (attached at `base_event`): `chain_uid`, `fingerprint`, `prev_event`, `signatures[]`, `authority_uid`; explicit ordinal at `metadata.sequence` | v1.9.0 | — | ✔ full `attestation_list` shape; ordinal at `unmapped.org_chain_seq` (P6) |
| — | Canonical serialization (cross-cutting for 4 and 8) | `fingerprint.serialization`/`serialization_id`; same pair on `digital_signature` | v1.9.0 | — | ✔ `serialization_id` 99 + named serialization string |
| 10 | Accounting decision (aggregate consumed / remaining vs. principal budget) | None — the v1.9.0 dictionary has **zero** attributes in this family (budget, quota, consumed, remaining, aggregate, spend all absent) | **Missing** | Unfiled — proposal offered in WS4 #172 if there's WG appetite | ✘ |

Legend: ✔ present in the reference bundle · ◐ partially present · ✘ absent · P*n* = producer gap
(§ below).

**Why row 8 satisfies "integrity-protected":** each event's `attestation_list[]` entry carries a
`fingerprint` over the event's canonical serialization and a `prev_event.fingerprint` equal to the
previous event's — a hash chain — plus `signatures[]` over the fingerprint. Sequence, timestamp,
and every other contract field on the event are inside the signed bytes, which is what makes rows
1–7 integrity-protected *when populated*: a field that rides `unmapped` is still covered by the
signature; a field that isn't emitted at all is covered by nothing. That is why the producer gaps
below are contract failures, not cosmetics.

**Why row 9 is a schema gap and not a producer gap:** a producer emitting `delegation` in full
conformance with v1.9.0 can still omit `parent_uid` (it is optional), and a consumer holding only
the event stream cannot reconstruct the subtree from single edges. Both halves are filed as
[ocsf#1739](https://github.com/ocsf/ocsf-schema/issues/1739).

## Schema gap register

| Gap | What's missing | Where it's tracked |
|---|---|---|
| Capability invoked | Tool/resource/prompt identity, serving system, transport, request/result correlator | [ocsf#1728](https://github.com/ocsf/ocsf-schema/issues/1728) |
| Declared configuration vs. executed | Tool-catalog version, adapter/artifact digests, declared/executed pairing | [ocsf#1724](https://github.com/ocsf/ocsf-schema/issues/1724) |
| Delegation lineage | `parent_uid` optionality; no materialised root; DAG description vs. singular parent | [ocsf#1739](https://github.com/ocsf/ocsf-schema/issues/1739) |
| Accounting decision | Aggregate consumed/remaining as an evidence field | Unfiled (offered in WS4 #172) |
| Cross-boundary causal binding | Resource owner's record naming the causing tool call (adjacent — the evidence complement of WS4 #172 §5 / Q9–Q10, not a contract row) | [ocsf#1738](https://github.com/ocsf/ocsf-schema/issues/1738) |

## Producer gaps (our own wire output, measured against this mapping)

Found by checking the reference bundle against the table — the point of shipping wire evidence is
that it cuts both ways.

- **P1 — `delegation` not emitted.** The gateway's export doesn't yet populate the `delegation`
  object, though the profile slot exists in 1.9.0. Until it does, contract row 2 is unmet in our
  own output.
- **P2 — policy version rides `unmapped.policy_version`,** not `policy.version` via
  `security_control`. Covered by the signature, invisible to a consumer keying on the schema slot.
- **P3 — `raw_data_hash` not emitted** as the request-digest slot; content hashes live inside the
  chained bytes instead.
- **P4 — denial reason absent:** denied events carry `action_id: 2` and `severity_id: 3` but no
  `status_code`/`status_detail` naming the violated rule.
- **P5 — `status` not emitted;** outcome is implied by `action_id`.
- **P6 — chain ordinal at `unmapped.org_chain_seq`** rather than `metadata.sequence`.

## Errata found while verifying

The merged attestation shape — in the v1.9.0 tag and unchanged on `main` — names the chain fields
**`fingerprint`** and **`prev_event`** (an object carrying the prior event's `fingerprint` plus
locator attributes). The draft-era names `entry_hash` / `prev_entry_hash` do not exist in the
merged schema. The reference bundle's **events** already emit the merged names; the bundle README's
prose used the draft names in several places and is corrected alongside this document. Any
external prose citing `attestation.entry_hash` should be read as `attestation_list[].fingerprint`.

One sample in this directory, [`attestation-finding-sample/`](./attestation-finding-sample/), still
carries events in a disclosed earlier-revision shape (singular `attestation`,
`entry_hash`/`prev_entry_hash`) — its README says so. Those events are signed material and cannot
be regenerated without the production key, so they remain as a dated historical artifact rather
than being edited in place.

## Version pinning

This mapping is pinned to **OCSF v1.9.0** and is only as good as that pin. Objects cited here that
were re-checked on `main` (`1.10.0-dev`) — `attestation`, `delegation`, the `ai_operation`
profile — are attribute-identical to v1.9.0 as of the verification date. Proposed fields
([ocsf#1728](https://github.com/ocsf/ocsf-schema/issues/1728),
[ocsf#1724](https://github.com/ocsf/ocsf-schema/issues/1724),
[ocsf#1739](https://github.com/ocsf/ocsf-schema/issues/1739)) are marked as proposed and must not
be cited as landed until they merge; when 1.10 releases, every row above gets re-verified against
the new tag before the pin moves.
