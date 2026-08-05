## Welcome back to Exhibit A.

Issue 02 ended on a line I have not stopped thinking about: *evidence is what an outside party can verify without trusting the entity that produced it.*

That sentence has an uncomfortable implication for everyone selling AI governance, including me. If every vendor invents its own private format for "here is what our agent did, and here is the proof" — then verifying any of it means learning a dozen proprietary schemas and trusting each vendor's own tooling to read its own records. That is not evidence anyone can independently verify. That is a dozen more piles of logs with nicer branding.

So this week's exhibit is not a breach, and it is not a model. It is a schema.

---

# The Paper Trail Went Public

For the last few months, the most important work I have done has not shipped in our product. It was proposed, in the open, into a standard nobody owns.

On August 3rd, it shipped in that standard's release.

I want to walk through what landed, because the *shape* of it is the argument this newsletter has been making since Issue 01 — and because I think the mechanism matters more than the milestone.

## The gap

A real forensic record for an AI agent has to answer three things: **who acted, that it happened and cannot be denied, and that anyone can check the proof without trusting us.** We can build all three into our own gateway — and we have. But if the format is one only we can read, the third one quietly fails. "Anyone can verify it" turns back into "trust our tooling," which is the exact problem we started with.

The fix is not a better proprietary feature. The fix is a shared vocabulary.

There is an open, vendor-neutral schema for security telemetry called **OCSF** — the Open Cybersecurity Schema Framework. When a security team investigates an incident, the events they pivot through are increasingly in this shape. It is the closest thing the industry has to a common language for "what happened," and the tools your SOC already runs are learning to speak it.

What it did not have was a clean, first-class way to say the thing this whole newsletter is about:

> *An AI agent did this — under this authority — and here is proof you can verify yourself.*

That gap was not an oversight. The standard was built for a world of users, services, and devices. The agents are new. So a few of us proposed the missing pieces.

## Three pieces, one argument

All three are now in [**OCSF 1.9.0**](https://github.com/ocsf/ocsf-schema/releases/tag/1.9.0), released August 3rd, 2026.

**1. Identity — *who* acted.**
A first-class `ai_agent` object: an AI agent represented as its own kind of actor, distinct from the human behind it and from the security sensor watching it. This one is [Ania Kacewicz's work](https://github.com/ocsf/ocsf-schema/pull/1641); I have been building on top of it. Without it, every agent action is anonymous after the fact — a service account and a shrug.

**2. Proof — *that it happened, and cannot be denied.***
An [`attestation` object and a `record_integrity` profile](https://github.com/ocsf/ocsf-schema/pull/1661): a signed, tamper-evident commitment that travels with the event, so a later edit, deletion, or reordering is detectable. This is the non-repudiation layer — the difference between "we say this happened" and "this is signed, and here is the signature."

**3. Verification — *that anyone can check it.***
A small but stubborn detail. When you sign structured data, the same logical record can be written to bytes more than one way, and a signature only verifies if the signer and the verifier produce the *exact* same bytes. So [`serialization_id`](https://github.com/ocsf/ocsf-schema/pull/1662) records which canonicalization was used — which means a third party, on different software, can reproduce the signed bytes and check the signature themselves.

That third one is the least glamorous and the one I care about most. It is the literal mechanism behind Issue 02's closing line. Without it, "verifiable" is a marketing word.

> **Trust Root pillar:** A record becomes evidence at the moment a stranger can verify it without your help. Identity says who, attestation says it is real, and canonical serialization is what lets someone you have never met confirm the proof on their own machine.

## Why a standard, and not a moat

The obvious business move was to build all of this into our gateway, keep the format to ourselves, and call it a competitive advantage. Verification you can only do with our tools is, after all, a reason to keep paying us.

That instinct is exactly backwards.

The trust root for an agent economy cannot be a thing one company owns. If AI Identity is the only party who can verify an AI Identity record, then we are not a trust root — we are just another vendor asking you to trust our logs, which is the posture I spend every issue of this newsletter arguing against.

So the vocabulary went into a standard we do not control, where our competitors can use it for free, and where the specification outlives us. That is not altruism and it is not a giveaway. It is the only version of this that actually works. A trust root you own is not a trust root. It is a dependency.

## What this does and does not mean

Precision is the whole brand here, so let me be exact about the size of this.

**What it means:** the vocabulary exists. If you want to emit an agent action as a signed, independently verifiable record, there is now a standard shape for it — in a schema your security tooling is already adopting, maintained by people who do not work for me. You do not have to invent it, and you do not have to ask my permission.

**What it does not mean:** that anyone is using it yet. A merged schema is a published grammar, not an installed base. Vendors have to emit it, SIEMs have to parse it, and auditors have to learn to ask for it. That is a multi-year adoption problem and it has barely started. I would rather tell you that plainly than let a release note do the overclaiming for me.

The honest status is: the hard part of *specifying* it is done, in public, permanently. The hard part of *adopting* it is entirely ahead.

Three follow-on proposals are open right now and targeted at the next release — carrying signature bytes on the signature object, per-node authority for delegation chains, and normalized stop reasons for agent operations. Those are still under review. I will report back the same way, whether they land or stall.

---

## The bottom line

*A forensic record only counts as evidence if the person auditing you can read and verify it without your help. As of August 3rd, the words for saying that are public, free, and not ours. That was always the point.*

---

## One question to take into your week

Look at whatever AI governance or audit tooling your team uses or is evaluating. Ask the vendor one question:

> *"If we leave you, can we still verify the records you produced for us — using software that isn't yours?"*

If the answer is no, you do not have evidence. You have a dependency.

The whole reason to put this in an open standard is so that the answer can be yes — including when the vendor is me.

---

### Until next time

If you have wrestled with agent logging, attestation, or audit formats in production — or if you have opinions about what the next version of this should look like — reply to this email or find me on LinkedIn. I read everything, and this is the rare topic where reader pushback can literally end up in a standard.

If you want help figuring out what any of this means for your own agent deployments, that is what [**ai-identity.co/advisory**](https://www.ai-identity.co/advisory) is for.

**— Jeff**

*Jeff Leva is the founder of [AI Identity](https://www.ai-identity.co), building durable identity and tamper-evident forensics for AI agents.*
