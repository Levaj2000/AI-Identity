# AI Identity — Compliance Readiness Tracker

Last updated: 2026-04-06

## Quick Reference for Prospect Conversations

When a prospect asks "Are you SOC 2 / HIPAA / etc. certified?" — here's what to say:

> "Our architecture is designed to meet [framework] requirements from day one — per-agent identity, tamper-proof audit trails, encryption at rest and in transit, tenant isolation, and fail-closed enforcement. We're pursuing formal certification as we scale, but I'm happy to walk you through exactly how our controls map to [framework]."

---

## Framework Status Overview

| Framework | Status | Architecture Ready? | Formally Certified? | Priority |
|-----------|--------|--------------------|--------------------|----------|
| SOC 2 Type II | Designed, not certified | Yes | No — plan post-Series A | High |
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
| Security | Encryption in transit | TLS 1.2+ on all endpoints | HTTPS enforced, Render TLS |
| Security | Encryption at rest | AES-256 encrypted credential vault | Upstream credentials model |
| Security | Audit logging | HMAC-SHA256 tamper-proof audit chain | Audit log + chain verification |
| Security | Change management | Git-based deployments, PR reviews | GitHub repo history |
| Availability | System monitoring | Health endpoints, Render monitoring | /health endpoint, uptime |
| Processing Integrity | Input validation | Request validation on all endpoints | API router validation |
| Confidentiality | Tenant isolation | Row-level security (RLS) in PostgreSQL | RLS policies, migration files |
| Confidentiality | Data classification | Agents never see raw provider credentials | Credential proxy architecture |

### Gaps to Close Before Certification
- [ ] Formal security policies documented (acceptable use, incident response, etc.)
- [ ] Penetration test by third party
- [ ] Business continuity / disaster recovery plan documented
- [ ] Vendor risk assessments (Render, Neon, Clerk)
- [ ] Employee security training (N/A until employees, but document the policy)
- [ ] Engage SOC 2 auditor (estimated cost: $20-50K)

### Timeline
Target: 6-12 months post-first-paying-customer or post-funding, whichever comes first.

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
- [ ] Verify Render and Neon can sign BAAs (or plan migration)

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
> Currently US-based (Render US, Neon US East). EU hosting available on Enterprise tier (planned).

**"Can we see your security documentation?"**
> Yes — ai-identity.co/security covers our architecture. Happy to do a deeper technical walkthrough.

**"Who are your subprocessors?"**
> Render (compute), Neon (database), Clerk (authentication). Full subprocessor list available on request.

**"Do you have cyber insurance?"**
> Not yet. Planned alongside SOC 2 certification.

**"Can we do a vendor security assessment?"**
> Absolutely. Send us your security questionnaire and we'll complete it.
