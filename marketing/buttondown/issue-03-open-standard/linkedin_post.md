# LinkedIn feed post — drives to the "Paper Trail Went Public" article

Status: DRAFT for Jeff to review and post from his own account.
First two lines are the hook (LinkedIn truncates there — they must earn the "see more" click).
Post the article first, then this post with the article link.

---

We could have kept it. The obvious move was to build agent attestation into our own product, keep the format private, and call it a competitive advantage — verification you can only do with our tools is a great reason to keep paying us.

We put it in a standard we don't own instead, where our competitors can use it for free.

On August 3rd it shipped in OCSF 1.9.0. Three pieces, and the order matters:

→ **Identity** — a first-class `ai_agent` object, so an agent is its own kind of actor rather than an anonymous service account. That one is Ania Kacewicz's work; I built on top of it.

→ **Proof** — an `attestation` object and `record_integrity` profile, so a later edit, deletion, or reordering of a record is detectable.

→ **Verification** — `serialization_id`, which records how the data was canonicalized before signing. Least glamorous, and the one I care about most: without it, a third party can't reproduce the signed bytes, and "verifiable" is just a marketing word.

The reasoning is simple enough to fit in one line: **a trust root you own is not a trust root. It is a dependency.**

If we're the only party who can verify a record we produced, we're not a trust root — we're just another vendor asking you to trust our logs.

One honest caveat, because release notes tend to overclaim on an author's behalf: a merged schema is a published grammar, not an installed base. Vendors still have to emit it, SIEMs have to parse it, auditors have to learn to ask for it. The hard part of specifying this is done. The hard part of adopting it is entirely ahead.

I wrote up the full reasoning — including what it doesn't prove — here: [ARTICLE LINK]

And a question worth asking whatever governance tooling you're evaluating: *if we leave you, can we still verify the records you produced for us, using software that isn't yours?*

If the answer is no, that's not evidence. That's a dependency.

#AIAgents #AIGovernance #OCSF #AIsecurity
