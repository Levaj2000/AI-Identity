# Compliance export profiles — scoping

**Status:** Draft — scopes the export data model for Milestone #34 (due 2026-06-20).
**Owner:** CTO
**Last reviewed:** 2026-04-17
**Feeds:** #273 (API shape + data model), downstream compliance work.
**Acceptance gate:** every framework requirement cited to its published text; gaps flagged explicitly.

## Purpose

Define what AI Identity's compliance export API must produce for each
target framework so that a customer's auditor can drop our output
into their evidence collection with minimal transformation. This
document does **not** design the API — that's #273 — but it locks the
shape of the evidence so the API design has a concrete target.

Three profiles in v1:

1. **SOC 2 Type II** (AICPA Trust Services Criteria)
2. **EU AI Act** (Regulation (EU) 2024/1689)
3. **NIST AI Risk Management Framework** (NIST AI 100-1)

Each profile specifies: what the framework asks for, what AI Identity
already captures, what we need to add to the export, and retention/
format expectations.

## Terminology

- **Profile** — a named export shape targeting one framework
  (e.g., `profile=soc2_tsc_2017`).
- **Evidence artifact** — a bounded chunk of export data that maps to
  a specific control or article requirement (e.g., "access log CSV
  covering the audit period").
- **Audit period** — the time range the export covers. SOC 2 Type II
  defaults to 12 months; customer-supplied for EU AI Act / NIST.
- **Required** vs **recommended** — required fields are mandatory for
  a valid export; recommended fields improve auditor usability but
  don't block a compliant export.

## Cross-cutting design decisions

These apply to every profile.

### Format

- **Archive format:** ZIP with a manifest (`manifest.json`) at the
  root enumerating every artifact, its SHA-256, and the framework
  control it satisfies. Auditors receive one file per export request.
- **Per-artifact format:** CSV for tabular data (access logs, change
  logs, check results), JSON for structured artifacts (attestations,
  config snapshots, incident records), PDF for human-readable
  narratives (the report cover letter).
- **Text encoding:** UTF-8, RFC 4180 CSV escaping, JSON per RFC 8259.
- **Dates:** ISO 8601 with explicit UTC (`Z` suffix). No local-time
  fields anywhere in the export.

Rationale: CSV is what Big 4 auditor tooling ingests without
transformation. JSON is lossless for structured fields. PDF is
expected for human-signed narratives. ZIP + manifest is the container
an auditor knows how to chain-of-custody.

### Integrity

Every export is bundled with a DSSE-signed manifest using the same
ECDSA P-256 KMS key that signs session attestations (see
[`../forensics/attestation-format.md`](../forensics/attestation-format.md)).
The manifest commits to the SHA-256 of every artifact in the archive.

This means an auditor can detect any tampering with the export after
it left our servers, without trusting our servers. Signature is
optional for internal-use exports; required for any artifact that
crosses a trust boundary.

### Retention

AI Identity retains the **ability to regenerate** an export
indefinitely — meaning the underlying evidence (audit log rows,
attestations, config snapshots) stays available subject to each org's
retention policy. Retention of the *exported archive itself* is the
customer's responsibility once downloaded; we don't warehouse a copy.

Customers should align their retention settings with the tightest
framework they target. See the per-profile sections below.

### Scope boundaries

Exports always scope to:

- A single org (no cross-tenant bundles).
- An explicit audit period (`start_date`, `end_date`).
- Optionally a single agent or subset of agents (for targeted evidence
  requests from an auditor's sampling plan).

Org-scoping is a hard invariant — bundling multiple orgs' evidence in
one archive would be a tenancy violation on par with signing across
orgs (see the attestation router's cross-org rejection in #263).

---

## SOC 2 Type II profile

**Target framework:** AICPA SOC 2, Trust Services Criteria (TSC), 2017 version with 2022 points of focus updates.
**Source text:** AICPA's [Trust Services Criteria](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) publication.
**Profile identifier:** `soc2_tsc_2017`.

### What SOC 2 Type II requires in evidence

Type II means **operating effectiveness over a period** (typically
12 months) — not a point-in-time snapshot. The audit period is the
defining parameter.

Specific TSC criteria AI Identity maps to:

| TSC | Control area | Evidence shape |
|---|---|---|
| **CC6.1** | Logical access controls over information assets | Per-agent policy bindings + enforcement log |
| **CC6.2** | Authentication and credential lifecycle | Key issuance/rotation/revocation log |
| **CC6.3** | Least privilege | Policy rules + any wildcard-permissive grants flagged |
| **CC6.6** | Key management lifecycle | Key lifecycle events including KMS forensic signer versions |
| **CC6.7** | Revocation completeness | Evidence that revoked agents have no active keys |
| **CC7.2** | Security event monitoring | Audit log with HMAC chain integrity + signed attestations |
| **CC7.3** | Incident response evaluation | Incident records (see #273 scope question below) |
| **CC8.1** | Change management | Policy + agent + key change log |
| **CC9.1** | Risk mitigation through vendor management | N/A — this is the customer's control over *us* |

Internal control codes (`SOC2-CC6.1`, etc.) already seeded in
`scripts/seed_compliance.py` map 1:1 to the TSC above.

### Required artifacts (v1 export)

1. **`access_log.csv`** — every `audit_log` row in the audit period.
   Maps to CC6.1, CC7.2. Columns: `id`, `created_at`, `agent_id`,
   `org_id`, `user_id`, `endpoint`, `method`, `decision`,
   `policy_version`, `correlation_id`, `entry_hash`, `prev_hash`.
2. **`change_log.csv`** — every agent-lifecycle event (create, policy
   change, key rotation, revocation). Maps to CC6.2, CC6.6, CC8.1.
3. **`attestations/<session_id>.dsse.json`** — every forensic
   attestation signed during the audit period. Maps to CC7.2.
4. **`chain_integrity.json`** — the result of
   `verify_chain(org_id, start, end)` at export time, signed. Maps to
   CC7.2 operating-effectiveness evidence.
5. **`control_results.csv`** — point-in-time snapshots of the
   automated compliance checks (every `ComplianceReport` row
   generated during the period). Maps to CC6.3, CC6.7, CC9.1.
6. **`manifest.json`** — DSSE-signed index. Covers integrity of the
   whole archive.

### Recommended artifacts

7. **`policy_snapshots/<timestamp>.json`** — the serialized policy
   object at each change point. Makes CC8.1 evidence self-contained
   (auditor doesn't need to reconstruct historical policy state).
8. **`agent_inventory.csv`** — every agent active at any point in the
   audit period with its lifecycle events. Useful for sampling.

### Retention expectations

- SOC 2 itself sets no numeric retention minimum; the audit period
  governs. Most SOC 2 attestations cover 12 months, so customers
  typically retain 12–24 months of evidence.
- **Our retention default:** 13 months for audit_log, 25 months for
  attestations + control_results (= audit period + 1 month buffer
  for late audits). Customers can raise.
- Forensic attestation envelopes should be retained **longer than**
  the audit log rows they commit to — see the Retention coordination
  section of [`../forensics/attestation-format.md`](../forensics/attestation-format.md).

### Known gaps (flagged for follow-up, not v1 blockers)

- **CC7.3 incident records**: we don't yet have a structured
  `incident_log` model. Current state: postmortems live as markdown
  in `docs/incident-response/`. v1 export will include a manifest
  entry pointing at the directory; a proper `IncidentRecord` table is
  a separate sprint item. Flagged in #273 design as a deferred field.
- **Vendor SOC 2 reports** (AI Identity's own): customers may ask
  for a pass-through of our Google Cloud / Neon / etc. SOC 2 reports.
  Out of scope for the export API; handled separately via the Trust
  Center.

---

## EU AI Act profile

**Target framework:** Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024.
**Source text:** [Official Journal OJ L, 2024/1689, 12.7.2024](https://eur-lex.europa.eu/eli/reg/2024/1689/oj).
**Profile identifier:** `eu_ai_act_2024`.
**Applicability:** v1 export targets **high-risk AI systems** per Article 6 / Annex III. General-Purpose AI model rules (Article 51+) and prohibited-practice disclosures (Article 5) are out of scope.

### What the EU AI Act requires in evidence

The Act imposes evidentiary burdens on *providers* and *deployers*
of high-risk AI systems. AI Identity sits at the deployer
infrastructure layer — our exports are designed to satisfy the
deployer's Article 26 obligations and support a provider's Annex IV
technical documentation.

Key articles with direct export implications:

| Article | Obligation | Evidence shape |
|---|---|---|
| **Art. 9** | Risk management system | Policy rules + change history + risk classification per agent |
| **Art. 10** | Data and data governance | Upstream data connector inventory (out of v1 — see gap) |
| **Art. 11** + **Annex IV** | Technical documentation | System description + architecture snapshot (see Annex IV coverage below) |
| **Art. 12** | Record-keeping (logging) | Audit log covering decisions, subjects, outcomes |
| **Art. 12(4)** | Logs tamper-evident + covering full lifecycle | HMAC chain + DSSE attestations |
| **Art. 13** | Transparency / information to deployers | Agent descriptions + capability declarations |
| **Art. 14** | Human oversight | Approval records (existing `ApprovalRequest` model) |
| **Art. 15** | Accuracy, robustness, cybersecurity | Credential encryption evidence + auth / circuit-breaker metrics |
| **Art. 19** | Log retention | **≥ 6 months** unless other EU/national law applies |
| **Art. 26(6)** | Deployer log retention | **≥ 6 months** for logs generated during operation |

Internal codes already seeded (`EUAI-TRANS-01`, `EUAI-ACC-01`, etc.)
map to these articles; see `scripts/seed_compliance.py`.

### Required artifacts (v1 export)

1. **`annex_iv_documentation.json`** — the Annex IV technical
   documentation fields we can produce automatically:
   - `1(a)` — general description of AI Identity system as deployed
   - `1(b)` — intended purpose (per-agent, from agent descriptions)
   - `2(a)` — methods and steps for development (references the
     architecture doc commit SHA at export time)
   - `2(d)` — logging and record-keeping capability description
     (references `../forensics/attestation-format.md` + this doc)
   - `3` — monitoring, functioning, and control description
     (references the audit log + attestations + ABAC policy engine)
2. **`access_log.csv`** — same shape as SOC 2 `access_log.csv`.
   Satisfies Article 12.
3. **`attestations/<session_id>.dsse.json`** — same as SOC 2.
   Satisfies Article 12(4) tamper-evidence requirement.
4. **`human_oversight_log.csv`** — every `ApprovalRequest` row
   (approved, denied, auto-expired). Satisfies Article 14.
5. **`agent_risk_classification.csv`** — per-agent declared risk
   category. **Gap:** we don't currently store this; see below.
6. **`policy_change_log.csv`** — policy version history. Satisfies
   Article 9 risk-management-system change evidence.
7. **`manifest.json`** — DSSE-signed index.

### Recommended artifacts

8. **`capability_disclosures.csv`** — per-agent capability set at
   each point in the period. Satisfies Article 13.3.
9. **`incident_records.json`** — same as SOC 2 (gap flagged).

### Retention expectations

- **Hard minimum: 6 months** for logs per Articles 12, 19, and 26(6).
- AI Identity's default is 13 months, which satisfies this
  comfortably. Customers operating under sector-specific EU law
  (finance, healthcare) may need longer.
- Annex IV documentation retention: **10 years** after the system is
  placed on the market (Article 18(1)). We don't retain the docs
  themselves that long — that's the provider's responsibility — but
  the export is generatable on demand from current-state data.

### Known gaps (flagged for #273 + follow-up items)

- **Risk classification per agent**: EU AI Act Annex III lists
  high-risk use cases by sector. We don't currently capture
  "this agent is a high-risk system under Annex III category 3(a)"
  on the agent model. Gap — proposal for #273: add
  `agent.eu_ai_act_risk_class` field (nullable, enum of Annex III
  categories + `not_in_scope`).
- **Data governance evidence (Article 10)**: governance of
  *upstream training data* is squarely the provider's responsibility
  and sits outside AI Identity's visibility. v1 export will
  acknowledge this limitation in the Annex IV section rather than
  fabricate evidence.
- **GPAI (Article 51) exports**: separate from high-risk. Out of
  scope for this profile; may be a separate `eu_ai_act_gpai` profile
  later if a design partner requests it.

---

## NIST AI RMF profile

**Target framework:** NIST AI Risk Management Framework (AI RMF 1.0).
**Source text:** [NIST AI 100-1, January 2023](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf), plus the [AI RMF Playbook](https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook) for suggested actions.
**Profile identifier:** `nist_ai_rmf_1_0`.
**Voluntary framework:** unlike the EU AI Act, AI RMF is guidance, not regulation. US federal contractors increasingly require it; customer-driven adoption.

### What NIST AI RMF requires in evidence

AI RMF organizes controls under four functions. AI Identity maps to
the operational-evidence subset of each — the policy/governance
questions (org-level risk posture, model lifecycle) are the
customer's responsibility, not ours.

| Function | Relevant subcategories | Evidence shape |
|---|---|---|
| **GOVERN** | GV-1.1 through GV-6.2 (policies, accountability) | Policy catalog + change log + role assignments |
| **MAP** | MP-4.1 (authorized use), MP-5.1 (impact) | Agent inventory + capability + risk classification |
| **MEASURE** | MS-2.5 (validity), MS-4.1 (monitoring), MS-4.3 (post-deployment) | Audit log + integrity verification + anomaly detection |
| **MANAGE** | MG-1.3 (mitigations), MG-2.4 (incident response), MG-3.1 (accountability) | Approval log + revocation log + incident records |

Internal codes already seeded (`NIST-GOV-01` through `NIST-MAN-01`)
map to these functions.

### Required artifacts (v1 export)

NIST does not prescribe an export format — it prescribes actions
(e.g., "document policy updates"). Our export satisfies the evidence
an auditor or internal risk team would request to verify those
actions.

1. **`govern.json`** — aggregated GOVERN evidence:
   - Policy catalog with version history
   - Org role assignments (from `OrgMembership`)
   - Agent-to-policy bindings
2. **`map.json`** — aggregated MAP evidence:
   - Agent inventory with capability declarations
   - Risk classification per agent (same field as EU AI Act — unified
     across profiles)
3. **`measure_audit_log.csv`** — access log, same shape as other
   profiles. Satisfies MS-4.1/MS-4.3 post-deployment monitoring.
4. **`measure_chain_integrity.json`** — chain verification at export
   time. Satisfies MS-2.5 validity evidence.
5. **`manage_approvals.csv`** — approval records. Satisfies MG-1.3
   mitigation application + MG-3.1 accountability.
6. **`manage_revocations.csv`** — agent + key revocation log.
   Satisfies MG-2.4 incident response applied to identity compromise.
7. **`manifest.json`** — DSSE-signed index.

### Recommended artifacts

8. **`anomaly_detections.csv`** — output of the anomaly-detection
   layer (deny clusters, cost outliers). Satisfies MS-4.1 continuous
   monitoring evidence.
9. **`control_results.csv`** — automated check results, same as
   SOC 2 + EU AI Act. Crosswalk to NIST function via the
   `ComplianceCheck.category` field.

### Retention expectations

- NIST AI RMF sets **no retention minimum**. Customer policy
  governs. Typical customer defaults: 12 months to match SOC 2.
- Where a single org targets SOC 2 + NIST, retention is governed by
  SOC 2's 12-month period — the tighter constraint wins.

### Known gaps

- **Impact assessment records** (MP-5.1): we don't capture
  deployment-time impact assessments — those are typically PDFs the
  customer authors externally. v1 export will allow customers to
  upload impact-assessment documents per-agent (new field); deferred
  to a post-#273 sprint item if design partners request it.
- **Bias/validity testing records** (MS-2.3, MS-2.5): model-level
  validity belongs to the provider, not to the runtime governance
  layer. Explicitly out of scope — called out in a `limitations`
  section of `map.json` so the auditor isn't left wondering.

---

## Cross-framework mapping

Many artifacts satisfy multiple frameworks. This table drives the
data model decision in #273: if an artifact appears in ≥ 2 profiles,
it becomes a first-class column in the export builder; if it's
profile-specific, it's assembled on demand.

| Artifact | SOC 2 | EU AI Act | NIST AI RMF |
|---|:---:|:---:|:---:|
| Access log (audit_log rows) | CC6.1, CC7.2 | Art. 12 | MS-4.1 |
| Change log (agent/policy/key) | CC8.1 | Art. 9 | GV-1.1 |
| Forensic attestations | CC7.2 | Art. 12(4) | MS-2.5 |
| Chain integrity verification | CC7.2 | Art. 12(4) | MS-2.5 |
| Control check results | CC6.3, CC6.7, CC9.1 | EUAI-TRANS-01 etc. | MS-4.1 |
| Agent inventory | CC6.1 | Annex IV 1(b) | MP-4.1 |
| Policy catalog + versions | CC6.1, CC8.1 | Art. 9 | GV-1.1 |
| Approval log | — | Art. 14 | MG-1.3 |
| Revocation log | CC6.7 | Art. 15 | MG-2.4 |
| Credential encryption evidence | CC8.1 | Art. 15 | GV-6.1 |
| Risk classification | — | Annex III | MP-5.1 |
| Incident records | CC7.3 | — | MG-2.4 |

**Core artifacts** (appear in all three profiles): access log,
change log, attestations, chain integrity, control results, agent
inventory, policy catalog. These are the seven columns #273's data
model must support natively.

**Profile-specific artifacts**: approval log (EU AI Act + NIST),
risk classification (EU AI Act + NIST), incident records (SOC 2 +
NIST — flagged gap).

---

## Data model sketch (feeds #273)

Concrete enough for #273 to start API design; deliberately not final.

```python
# New table: compliance_exports
class ComplianceExport(Base):
    id: UUID                       # export id, returned to client
    org_id: UUID                   # always org-scoped
    requested_by: UUID             # user_id
    profile: str                   # "soc2_tsc_2017" | "eu_ai_act_2024" | "nist_ai_rmf_1_0"
    audit_period_start: datetime
    audit_period_end: datetime
    agent_filter: list[UUID] | None  # optional narrowing
    status: str                    # "queued" | "building" | "ready" | "failed"
    archive_url: str | None        # signed URL once ready
    archive_sha256: str | None
    manifest_dsse: dict | None     # the DSSE envelope for the manifest
    created_at: datetime
    completed_at: datetime | None
```

```python
# New field on agents
class Agent(Base):
    # ...existing fields...
    eu_ai_act_risk_class: str | None  # Annex III category id or "not_in_scope"
    # NIST uses the same field (same framework question, different vocabulary)
```

Suggested API shape (details finalized in #273):

- `POST /api/v1/compliance/exports` — create
- `GET /api/v1/compliance/exports/{id}` — poll status + retrieve URL
- `GET /api/v1/compliance/exports` — list
- Async build via Cloud Run job or worker; don't tie up the API
  request for a 12-month access_log dump.

---

## Open questions resolved (or deferred) by this doc

- **Three profiles — right call?** Yes — SOC 2 + EU AI Act + NIST
  cover the stated target customer base (enterprise US + EU). ISO
  42001 and UK AI framework adoption are watch-items but not v1.
- **Should the export include the HMAC key?** No. The verify-key is
  the org's property, managed out-of-band. The export includes
  what the key verifies, not the key itself.
- **What if a customer has SOC 2 AND EU AI Act?** Run two exports or
  a combined one with both profile bundles inside — decision
  deferred to #273 API design.
- **What about HIPAA / GDPR / PCI DSS?** Partial coverage via the
  SOC 2 + EU AI Act profiles (HIPAA's audit-trail rules overlap
  heavily with SOC 2 CC7.2; GDPR Article 30 overlaps with EU AI Act
  Article 12). Separate profile added if a design partner requests.
- **Incident records — build now or later?** Later. Structured
  `incident_log` is a separate sprint item; v1 export will ship with
  a manifest-level pointer to unstructured incident docs.

## Next steps

1. **#273** consumes this doc to produce the API spec + migration.
2. **Flag raised** on the board: new field
   `agent.eu_ai_act_risk_class` needs a migration — log as a
   dependency of #273.
3. **Flag raised** on the board: `IncidentRecord` table is a gap for
   SOC 2 CC7.3 + NIST MG-2.4 — log as a post-Milestone-#34 item.
4. Review this doc with the first design partner targeting SOC 2 (if
   any on the Cisco call — see #277) before finalizing #273.

## References

- AICPA Trust Services Criteria, 2017 (with 2022 points of focus): https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022
- Regulation (EU) 2024/1689 (EU AI Act): https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- NIST AI Risk Management Framework (AI 100-1): https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf
- NIST AI RMF Playbook: https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook

Internal companion docs:

- [`../forensics/attestation-format.md`](../forensics/attestation-format.md) — the signed-envelope format referenced throughout
- [`../forensics/trust-model.md`](../forensics/trust-model.md) — what auditors can and can't conclude from an attestation
- `scripts/seed_compliance.py` — the already-seeded control codes this doc cross-references
