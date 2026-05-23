## Welcome to Exhibit A.

This is Issue 01.

Every week, I take one story — a model, a breach, a governance gap, a policy fight — and treat it as evidence. Evidence for the same argument: AI agents need identity, policy, and a paper trail. We're shipping powerful AI into real workflows faster than we're shipping the trust infrastructure around it, and every week another exhibit lands on the pile.

I'm Jeff Leva, founder of AI Identity. We build the durable identity and tamper-evident forensics layer for AI agents, so when something goes wrong you don't have to trust a vendor's logs — you have your own.

Let's start with the story everyone's already arguing about.

---

# DeepSeek as Exhibit A: Why AI Needs Identity and Forensics

DeepSeek is a useful narrative hook for a larger point: advanced AI systems are being adopted faster than trust, security, and evidence frameworks are being built around them. The strongest conclusion is not that one product looks risky — it is that the current AI market still treats many powerful models like ordinary software components even when they can access sensitive data, execute workflows, and influence real-world decisions.

## Why DeepSeek raised alarms

DeepSeek drew scrutiny because multiple analyses described a combination of privacy, security, and governance concerns — not one isolated flaw. Reported concerns include extensive data collection, storage of user data on servers in China, legal access risks tied to Chinese law, and technical weaknesses in mobile app security controls.

Several reviews also noted that DeepSeek's apps appeared to gather broad categories of information — chat content, device details, usage patterns. In practical terms, users cannot treat prompts as disposable when those prompts may contain business ideas, internal code, customer data, or operational context.

## The real issue is not only privacy

Privacy is the most visible concern, but the bigger issue is trust across the full lifecycle of an AI interaction. Once a model is integrated into real work, organizations need to know **which model acted, what data it saw, what tools it invoked, what policy should have applied, and what evidence remains after the fact.**

That is where many AI deployments break down. Traditional SaaS security assumes a user, an application, and a log trail. Agentic AI introduces probabilistic behavior, dynamic tool use, prompt-injection exposure, and third-party model dependencies that blur accountability. A breach or misuse event is harder to reconstruct when the system lacks strong identity, policy enforcement, and tamper-evident records.

> **Why this matters:** Logs are not evidence. If your incident response depends on trusting a vendor's own records, you do not have a forensic posture — you have a relationship.

## Why identity matters

Identity answers a basic but underappreciated question: *who, exactly, performed an action.* In human systems, that question is handled through accounts, roles, credentials, and access controls. In agentic systems, those same primitives are often incomplete or missing.

Without durable agent identity, every model call starts to look anonymous after the fact. That makes it difficult to separate an authorized workflow from a hijacked one, a policy-approved action from a prompt-injected action, or a legitimate orchestration step from an unsafe escalation.

## Why forensics matters

Forensics is what turns activity into evidence. Logging alone is not enough when an organization needs to investigate a sensitive event, brief leadership, support legal review, or demonstrate compliance to an auditor.

A credible AI forensics layer should preserve a verifiable chain of events: which identity initiated the task, what context was present, what policy was evaluated, what outputs were produced, and whether the record can be independently validated later. When that chain does not exist, incident response depends too heavily on trust in the vendor's own records and explanations.

## What DeepSeek illustrates for the market

DeepSeek is best understood as a warning sign for the broader AI ecosystem. The lesson is not that one vendor is imperfect; it is that organizations are rushing powerful AI capabilities into workflows before they have established model governance, data-handling boundaries, approved deployment patterns, and reliable forensic evidence.

The pattern will repeat with other models, open-weight systems, wrappers, and agent frameworks unless buyers demand stronger control planes around identity, policy, and auditability. The industry does not only need safer models — it needs infrastructure that makes AI actions **attributable, governable, and investigable.**

## Practical guidance

**For individuals.** Assume that any prompt sent to an untrusted AI service may be retained, analyzed, or exposed beyond the original interaction. Sensitive work, proprietary code, credentials, financial records, legal material, and regulated data should stay out of services with unresolved privacy or security concerns.

**For organizations.** Treat external AI models as untrusted execution components unless they are wrapped in enterprise controls: clear model approval standards, prompt and output handling rules, strong identity, policy enforcement, monitoring, and tamper-evident audit trails.

## The bottom line

*DeepSeek didn't break AI security. It revealed what was already broken: every powerful model deployed without identity, policy, or evidence is one incident away from looking just as risky.*

*The industry doesn't only need safer models. It needs infrastructure that makes AI actions **attributable, governable, and investigable.***

---

## One question to take into your week

Pick the AI tool your team uses most. Now answer four questions about its last sensitive action:

1. **Who** — which identity initiated it?
2. **What** — what data and tools were touched?
3. **Policy** — what rule was evaluated?
4. **Proof** — is the record tamper-evident?

If you can't answer all four, you have a DeepSeek-shaped gap. The model is irrelevant.

---

### See you next week

If a friend forwarded this, [subscribe here](https://exhibit-a.ai-identity.co) so you don't miss the next exhibit.

If you're a security leader, founder, or operator wrestling with these problems in production — hit reply. I read everything.

**— Jeff**

*Jeff Leva is the founder of [AI Identity](https://ai-identity.co), building durable identity and tamper-evident forensics for AI agents.*
