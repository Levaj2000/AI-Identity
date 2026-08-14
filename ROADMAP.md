# AI Identity — Product Roadmap

Last updated: 2026-08-14

## Now (August 2026)

Current focus is the standards footprint and cross-domain delegation — the work that
shipped in 0.3.0/0.4.0 and its follow-through:

| Workstream | Status | Notes |
|------------|--------|-------|
| OCSF / CoSAI WS4 standards contributions | Active | `ai_tool` object draft (v2), #1724 AI Agent Trust Inventory class draft, Trust Graph span-attribute proposal, OTel↔OCSF audit crosswalk. Built on the `attestation` object + `record_integrity` profile shipped in OCSF 1.9.0. |
| OTel Audit Logging initiative | Active | Supporter of open-telemetry/community#2409; sequence chain-scoping and signer-split observations incorporated into the spec draft. |
| Cross-domain delegation follow-through | Active | Biscuit mandate tokens + signed draw receipts shipped in 0.4.0; hardening and adoption follow-ups as they surface. |
| Founder advisory engagements | Active | `/advisory` live — agent identity & governance architecture, tamper-evident audit evidence, OCSF adoption. |

## Next — v0.5.0 "Enterprise Forensics" (target: Fri Sep 25, 2026)

The forensics scope originally penciled in for v0.4.0, now scheduled for real:

| Feature | Priority | Description |
|---------|----------|-------------|
| Forensic retention policies | High | Customer-defined data-retention, redaction, and sampling policies separate from runtime access policies. |
| Forensic capture modes | High | Deep capture for regulated flows, summarized capture for dev/test. Cost optimization at scale. |
| SIEM integrations — first native connector (Splunk HEC) | Medium | Groundwork shipped: generic webhook audit sink + NDJSON (HEC-shaped) export. Native transports tracked in #136; Splunk HEC first, Chronicle/Datadog/Panther on enterprise customer pull. |
| Design partner onboarding | High | Founder Rate (50% off Pro for 6 months) for first 5-10 customers with case study commitment. |

Checkpoint: mid-cycle scope review week of Sep 7 — anything not landed by then moves
to v0.6.0 rather than slipping the date.

## Later (Q4 2026 – Q1 2027)

| Feature | Priority | Description |
|---------|----------|-------------|
| Remaining SIEM connectors | Medium | Chronicle, Datadog, Panther transports on the #136 framework. Build when enterprise customer requests. |
| SOC 2 Type II certification | High | Formal audit and certification. Policies now at v1.1 with quarterly review cadence in place; need pen test and vendor risk assessments. Estimated $20-50K. |
| HIPAA BAA availability | High | Business Associate Agreement for healthcare customers. Requires legal review and infrastructure verification. |
| On-premise / VPC deployment | Medium | Enterprise tier feature for customers with data residency requirements. |
| Multi-region (EU hosting) | Medium | EU-based infrastructure option for GDPR data residency compliance. |
| Team roles and permissions | Medium | Role-based access within organizations (owner, operator, viewer). |

## Completed

| Feature | Version | Date |
|---------|---------|------|
| Cross-domain Biscuit mandate tokens + gateway enforcement | 0.4.0 | Aug 14, 2026 |
| Signed draw receipts (enforcement-point evidence up the delegation chain) | 0.4.0 | Aug 14, 2026 |
| OCSF 1.9.0 alignment (pin flip + regenerated WS4 reference bundle, 236 signed events) | 0.4.0 | Aug 14, 2026 |
| Compliance policy set to v1.1 (quarterly review cadence established) | 0.4.0 | Aug 14, 2026 |
| Supply-chain hardening: full lockfiles + hermetic image builds | 0.3.0 | Aug 4, 2026 |
| Pre-packaged export profiles (SOC 2 / EU AI Act / NIST AI RMF, machine-readable + PDF cover letter) | 0.3.0 | Aug 4, 2026 |
| Signed attestations (session attestation endpoint, bundled verifier, public Evidence Anchor checkpoints) | 0.3.0 | Aug 4, 2026 |
| Generic webhook audit sink + NDJSON SIEM-format export | 0.3.0 | Aug 4, 2026 |
| AI Forensics pillar elevation | 0.2.0 | Apr 6, 2026 |
| Four Pillars governance framework | 0.2.0 | Apr 6, 2026 |
| Industry pages (Healthcare, Finance) | 0.2.0 | Apr 6, 2026 |
| Automated inactive user cleanup (90-day) | 0.2.0 | Apr 6, 2026 |
| QA smoke test cleanup hardening | 0.2.0 | Apr 6, 2026 |
| Foundation release | 0.1.0 | Mar 29, 2026 |
