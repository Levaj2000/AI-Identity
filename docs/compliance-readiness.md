# AI Identity — Compliance Readiness Tracker

Last updated: 2026-08-05

## Quick Reference for Prospect Conversations

When a prospect asks "Are you SOC 2 / HIPAA / etc. certified?" — here's what to say:

> "Our architecture is designed to meet [framework] requirements from day one — per-agent identity, tamper-evident audit trails, encryption at rest and in transit, tenant isolation, and fail-closed enforcement. We're pursuing formal certification as we scale, but I'm happy to walk you through exactly how our controls map to [framework]."

---

## Framework Status Overview

| Framework | Status | Architecture Ready? | Formally Certified? | Priority |
|-----------|--------|--------------------|--------------------|----------|
| SOC 2 Type II | Designed, not certified | Yes | No — triggered by first enterprise contract | High |
| ISO 42001 (AI management) | Evaluating | Partially | No | Medium — credibility signal for an AI-governance vendor |
| EU AI Act | Compliant by design | Yes | N/A (no certification body yet) | High |
| HIPAA | Controls in place | Yes | No BAA available yet | High |
| NIST AI RMF | Aligned | Yes | N/A (voluntary framework) | Medium |
| GDPR | Partial | Mostly | No DPA template yet | Medium |
| ISO 27001 | Not started | Partially | No | Low (for now) |
| PCI DSS | Not applicable | N/A | N/A | None |

---

## SOC 2 Type II

### What Prospects Ask
"Are you SOC 2 certified?"

### Honest Answer
"Not yet — we're pre-certification. Our architecture is designed for SOC 2 from the ground up. Here's what's in place today."

### Controls Already In Place

| Trust Principle | Requirement | AI Identity Control | Evidence |
|----------------|-------------|--------------------| ---------|
| Security | Logical access controls | Per-agent API keys with scoped permissions | Agent detail page, key management |
| Security | Encryption in transit | TLS 1.2+ on all endpoints | HTTPS enforced, Google-managed TLS on GKE ingress |
| Security | Encryption at rest | AES-256 encrypted credential vault | Upstream credentials model |
| Security | Audit logging | HMAC-SHA256 tamper-evident audit chain; KMS-signed attestations (DSSE, ECDSA P-256) | Audit log + chain verification, attestation format spec |
| Security | Change management | Git-based deployments, PR reviews | GitHub repo history |
| Availability | System monitoring | Health endpoints, GKE + Google Managed Prometheus | /health and /health/deep endpoints, uptime |
| Processing Integrity | Input validation | Request validation on all endpoints | API router validation |
| Confidentiality | Tenant isolation | Row-level security (RLS) in PostgreSQL | RLS policies, migration files |
| Confidentiality | Data classification | Agents never see raw provider credentials | Credential proxy architecture |

### Gaps to Close Before Certification
- [ ] Formal security policies documented — 3 of ~13 done (Access Management, Change Management, Incident Response in `docs/compliance/`, all v1.1 reviewed 2026-08-05); remainder via compliance-platform templates: Information Security (master), Acceptable Use, Data Classification, Cryptography, Vendor Management, BC/DR, Risk Assessment, Secure SDLC, Data Retention & Disposal, Vulnerability Management
- [ ] Penetration test by third party
- [ ] Business continuity / disaster recovery plan documented
- [ ] Vendor risk assessments (Google Cloud, Neon, MongoDB Atlas, Clerk, Vercel, Render)
- [ ] Employee security training (N/A until employees, but document the policy)
- [ ] Engage SOC 2 auditor (estimated cost: $20-50K — unverified; replace with real quotes)

### Timeline
Trigger: first enterprise contract that requires SOC 2. Kickoff sized for a start within 6-18 months; Type II requires an observation window (typically 3-12 months) after controls are live.

---

## EU AI Act

### What Prospects Ask
"How does this help us comply with the EU AI Act?"

### Honest Answer
"AI Identity is built specifically for EU AI Act compliance. We cover the key requirements for high-risk AI systems."

### Requirements Mapping

| EU AI Act Requirement | Article | AI Identity Control |
|----------------------|---------|--------------------|
| Risk management system | Art. 9 | Policy enforcement with deny-by-default gateway |
| Data governance | Art. 10 | Per-agent scoped permissions, credential isolation |
| Technical documentation | Art. 11 | Tamper-proof audit logs with full request metadata |
| Record-keeping | Art. 12 | HMAC-SHA256 chained audit trail, configurable retention |
| Transparency | Art. 13 | Agent identity, capability declarations, decision logging |
| Human oversight | Art. 14 | Human-in-the-loop approval gates (Enterprise) |
| Accuracy & robustness | Art. 15 | Fail-closed architecture, anomaly detection |
| Conformity assessment | Art. 43 | Compliance evidence export, automated assessments |

### Status
Strong coverage. No formal certification exists yet for EU AI Act (enforcement bodies still forming). AI Identity's architecture is ahead of most competitors here.

---

## HIPAA

### What Prospects Ask
"Can we use this for healthcare AI agents handling PHI?"

### Honest Answer
"Our controls align with HIPAA requirements — per-agent access controls, audit trails, encryption. We don't have a BAA (Business Associate Agreement) available yet, which is required before you can send us PHI."

### Controls Mapping

| HIPAA Requirement | AI Identity Control |
|-------------------|--------------------|
| Unique user identification (164.312(a)(2)(i)) | Per-agent identity with unique API keys |
| Audit controls (164.312(b)) | Tamper-proof audit log with agent attribution |
| Access control (164.312(a)(1)) | Scoped permissions, deny-by-default gateway |
| Transmission security (164.312(e)(1)) | TLS encryption on all endpoints |
| Integrity controls (164.312(c)(1)) | HMAC-SHA256 chain verification |
| Minimum necessary (164.502(b)) | Per-agent capability scoping |

### Gaps to Close
- [ ] Business Associate Agreement (BAA) template — need legal review
- [ ] HIPAA-specific data handling documentation
- [ ] Incident response plan specific to PHI breaches
- [ ] Verify Google Cloud, Neon, and MongoDB Atlas can sign BAAs (or plan migration)

### Timeline
BAA availability target: when first healthcare design partner is ready to go to production.

---

## NIST AI RMF

### What Prospects Ask
"How do you align with the NIST AI Risk Management Framework?"

### Honest Answer
"We align with NIST AI RMF across all four core functions."

### Alignment

| NIST AI RMF Function | AI Identity Coverage |
|---------------------|---------------------|
| GOVERN | Policy-as-code, versioned agent configurations, role-based access |
| MAP | Agent capability declarations, scoped permissions, risk categorization |
| MEASURE | Continuous monitoring, anomaly detection, audit log analytics |
| MANAGE | Human-in-the-loop gates, fail-closed enforcement, automated remediation |

### Status
Strong alignment. NIST AI RMF is voluntary — no certification needed. Reference it in sales conversations with US government and enterprise prospects.

---

## GDPR

### Controls In Place
- Data encryption at rest and in transit
- Tenant isolation via RLS
- Audit logging of all data access
- No unnecessary data collection

### Gaps to Close
- [ ] Data Processing Agreement (DPA) template
- [ ] Data Subject Access Request (DSAR) process documented
- [ ] Privacy policy reviewed for GDPR-specific language
- [ ] Data retention policy formalized (beyond audit log retention tiers)
- [ ] Cookie consent on marketing site (if applicable)

---

## Prospect FAQ Cheat Sheet

**"Are you SOC 2 certified?"**
> Not yet. Architecture is SOC 2-ready. Certification planned post-funding. Happy to walk through our controls.

**"Do you have a BAA?"**
> Not yet. Our HIPAA controls are in place. BAA is on the roadmap — what's your timeline?

**"How do you handle data residency?"**
> Currently US-based (Google Cloud, Neon US East). EU hosting available on Enterprise tier (planned).

**"Can we see your security documentation?"**
> Yes — ai-identity.co/security covers our architecture. Happy to do a deeper technical walkthrough.

**"Who are your subprocessors?"**
> Google Cloud (compute, KMS), Neon (database), MongoDB Atlas (Mandate Service), Clerk (authentication), Vercel (marketing site). Full subprocessor list available on request.

**"Do you have cyber insurance?"**
> Not yet. Planned alongside SOC 2 certification.

**"Can we do a vendor security assessment?"**
> Absolutely. Send us your security questionnaire and we'll complete it.

---

## Compliance Cost Model (to fill from vendor quotes)

Line items for planning — replace estimates with real quotes from compliance-automation
platform conversations (Vanta / Drata / Secureframe class):

| Line item | Quoted cost | Notes |
|-----------|------------|-------|
| Automation platform annual fee | TBD | Ask for smallest tier / early-stage pricing |
| SOC 2 Type I audit (partner auditor) | TBD | |
| SOC 2 Type II audit (partner auditor) | TBD | Confirm observation-window length |
| Third-party penetration test | TBD | Required for SOC 2; ask if bundled |
| ISO 42001 add-on (later) | TBD | Incremental cost on same platform |

Company inputs that drive pricing: solo founder (1 employee), stack = Google Cloud (GKE),
GitHub, GitHub Issues/Projects, Google Workspace (corporate IdP). Clerk is product-side
customer auth, not the corporate IdP.
