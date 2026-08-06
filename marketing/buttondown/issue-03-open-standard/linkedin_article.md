# The Paper Trail Went Public

**TL;DR.** My company sells tamper-evident forensics for AI agents. The most important work we did this year did not ship in our product — it shipped in OCSF 1.9.0, an open standard we do not own, where our competitors can use it for free. This is why that was the only version of the idea that actually works, and an honest accounting of how little it proves so far.

---

Here is an uncomfortable implication for everyone selling AI governance, including me.

If every vendor invents its own private format for "here is what our agent did, and here is the proof," then verifying any of it means learning a dozen proprietary schemas and trusting each vendor's own tooling to read its own records. That is not evidence anyone can independently verify. That is a dozen more piles of logs with nicer branding.

A real forensic record for an AI agent has to answer three things: **who acted, that it happened and cannot be denied, and that anyone can check the proof without trusting the vendor.** You can build all three into your own product — we did. But if the format is one only you can read, the third one quietly fails. "Anyone can verify it" turns back into "trust our tooling," which is the exact problem we started with.

The fix is not a better proprietary feature. The fix is a shared vocabulary.

## The standard that already exists

There is an open, vendor-neutral schema for security telemetry called **OCSF** — the Open Cybersecurity Schema Framework. When a security team investigates an incident, the events they pivot through are increasingly in this shape. It is the closest thing the industry has to a common language for "what happened," and the tools your SOC already runs are learning to speak it.

What it did not have was a first-class way to say the thing that matters here:

> *An AI agent did this — under this authority — and here is proof you can verify yourself.*

That gap was not an oversight. The standard was built for a world of users, services, and devices. The agents are new. So a few of us proposed the missing pieces.

## What landed in 1.9.0

All three are in [OCSF 1.9.0](https://github.com/ocsf/ocsf-schema/releases/tag/1.9.0), released August 3rd, 2026.

**1. Identity — who acted.** A first-class `ai_agent` object: an AI agent represented as its own kind of actor, distinct from the human behind it and from the security sensor watching it. This one is [Ania Kacewicz's work](https://github.com/ocsf/ocsf-schema/pull/1641); I built on top of it. Without it, every agent action is anonymous after the fact — a service account and a shrug.

**2. Proof — that it happened, and cannot be denied.** An [`attestation` object and a `record_integrity` profile](https://github.com/ocsf/ocsf-schema/pull/1661): a signed, tamper-evident commitment that travels with the event, so a later edit, deletion, or reordering is detectable. The difference between "we say this happened" and "this is signed, and here is the signature."

**3. Verification — that anyone can check it.** A small, stubborn detail. When you sign structured data, the same logical record can be serialized to bytes more than one way, and a signature only verifies if signer and verifier produce the *exact* same bytes. So [`serialization_id`](https://github.com/ocsf/ocsf-schema/pull/1662) records which canonicalization was used — which lets a third party, on different software, reproduce the signed bytes and check the signature themselves.

That third one is the least glamorous and the one I care about most. Without it, "verifiable" is a marketing word.

## Why a standard, and not a moat

The obvious business move was to build all of this into our own gateway, keep the format to ourselves, and call it a competitive advantage. Verification you can only perform with our tools is, after all, a reason to keep paying us.

I think that instinct is exactly backwards.

The trust root for an agent economy cannot be a thing one company owns. If we are the only party who can verify a record we produced, we are not a trust root. We are just another vendor asking you to trust our logs.

So the vocabulary went into a standard we do not control, where competitors can use it for free, and where the specification outlives the company. That is not altruism. It is the only version of this that works. **A trust root you own is not a trust root. It is a dependency.**

## What this does not mean

Let me be exact about the size of this, because release notes tend to overclaim on an author's behalf.

**What it means:** the vocabulary exists. If you want to emit an agent action as a signed, independently verifiable record, there is now a standard shape for it — in a schema your security tooling is already adopting, maintained by people who do not work for me. You do not have to invent it, and you do not need my permission.

**What it does not mean:** that anyone is using it yet. A merged schema is a published grammar, not an installed base. Vendors have to emit it, SIEMs have to parse it, and auditors have to learn to ask for it. That is a multi-year adoption problem and it has barely started.

The honest status: the hard part of *specifying* this is done, in public, permanently. The hard part of *adopting* it is entirely ahead. Three follow-on proposals are open now and targeted at the next release — signature bytes on the signature object, per-node authority for delegation chains, normalized stop reasons for agent operations. Still under review. I will report back either way.

## One question to take into your week

Look at whatever AI governance or audit tooling your team uses or is evaluating, and ask the vendor one question:

> *"If we leave you, can we still verify the records you produced for us — using software that isn't yours?"*

If the answer is no, you do not have evidence. You have a dependency.

The whole reason to put this in an open standard is so the answer can be yes — including when the vendor is me.

---

If you have wrestled with agent logging, attestation, or audit formats in production, I would genuinely like to hear how it went. Comments or DMs both work — this is the rare topic where pushback can end up in a standard.

*Jeff Leva is the founder of [AI Identity](https://www.ai-identity.co), building durable identity and tamper-evident forensics for AI agents. Advisory work: [ai-identity.co/advisory](https://www.ai-identity.co/advisory).*

---

---

> ### 📝 What to watch for (reviewer's note — delete before posting)
>
> In priority order:
>
> 1. **Your advisory post on 8/5 already said "my agent-attestation work shipped in the OCSF 1.9.0 release."** So for your LinkedIn audience this is not news — it is the substance behind a line they already scrolled past. I wrote it that way on purpose (mechanism, reasoning, honest limits, not announcement), but it changes the *timing*: posting this within a day or two of the advisory post reads as repeating yourself. My vote is to let it breathe a week, so it lands as "here's the depth" rather than "here's my news again."
> 2. **Naming Ania Kacewicz.** Her PR is public, merged, and now in a shipped release under her name, so crediting her is accurate and gracious — and it visibly positions you as someone who builds *on* colleagues' work rather than around it. But a marketing post is a different surface than a code credit, and this circulates. A quick heads-up to her before you post is the right move; if you'd rather not, "a fellow contributor" reads fine and I can swap it in 30 seconds.
> 3. **"Where our competitors can use it for free" is a flag you're planting, not a neutral fact.** It's a strong stance and consistent with the trust-root thesis, but it is quotable and it does foreclose a future "actually our format is proprietary" pivot. Worth a beat of consideration, not a change — I think it's the best line in the piece.
> 4. **The "What this does not mean" section is a deliberate brake on your own hype.** It costs you some punch. It is also the single most on-brand thing in the article and the reason a skeptical reader will trust the rest of it. If you cut anything for length, cut elsewhere.
> 5. **Every "subscribe" CTA is gone.** `exhibit-a.ai-identity.co` and `buttondown.com/exhibit-a` both 404, and your own `probe-signup/route.ts` says the slug never existed. If you actually do have a Buttondown list under a different name that I couldn't find, say so and I'll put the CTA back in both versions.
> 6. **Re-check the three open PRs the morning you post.** #1704, #1705, and #1709 were all open and unmerged as of 2026-08-05. If one lands overnight, "still under review" becomes wrong — and being wrong about your own merge status is the one error this particular piece cannot afford.
> 7. **Nothing internal made it in.** No maintainer dynamics, no core-vs-extension discussion, no IBM specifics beyond what's already public on your advisory page. The piece is built entirely from links a stranger can open and check, which is the correct posture for an article whose whole argument is "verify it without trusting me."
