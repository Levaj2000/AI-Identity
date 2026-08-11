# Draft response for open-telemetry/community#2409 — paste as Jeff

**Context:** Hilmar Falkenberg (SAP, @hilmarf) incorporated our two OCSF
observations into the Audit Logging spec draft
([apeirora/opentelemetry-specification@578b930](https://github.com/apeirora/opentelemetry-specification/commit/578b930))
and invited us to join the initiative as a supporter (2026-08-11 email /
PR comment). Background on the group: SAP-led (sponsors SAP + Microsoft,
filed by @mlenkeit Oct 2024), developed in the `apeirora` org — SAP's
IPCEI-CIS EU sovereign-cloud program — after the OTel Governance Committee
declined formal SIG status in Oct 2025; the PR thread remains the proposal
venue. Full assessment in the 2026-08-11 session notes.

**Posting notes:** paste the body below verbatim as a reply comment on
[open-telemetry/community#2409](https://github.com/open-telemetry/community/pull/2409).
Both artifact links are live on `main`. Points 1–3 map to gaps verified
absent from 578b930 as of 2026-08-11 — none of it duplicates what Hilmar
already incorporated.

---

Thanks @hilmarf — happy to join as a supporter, please add me. The corner I
can usefully hold is the OCSF↔OTel intersection: we run the OCSF side of
this in production (hash-chained, per-event-signed audit exports under the
`record_integrity` profile that landed in OCSF 1.9 via
ocsf/ocsf-schema#1661), and my interest is that the two specs end up
mutually verifiable rather than parallel.

I read through 578b930 — both additions are the right calls.
`audit.sequence.stream_id` resolves the demultiplexing problem cleanly, and
the `audit.integrity.signer` language that producer and collector signatures
"MUST NOT be treated interchangeably" is exactly the discipline this needs:
point-of-action attestation and custody attestation answer different
questions, and we learned to keep them separate the slow way.

A few notes from having shipped this shape, in roughly descending order of
how much round-trip they might save you:

1. **A chain pointer needs a resolvable record identifier, not only a
   hash.** A predecessor hash proves linkage but can't *locate* the
   predecessor across storage, sharding, or retention boundaries. OCSF's
   merged shape ended up requiring every event to carry `metadata.uid` and
   the previous-record pointer to reference it (`prev_event.uid`), with the
   hash binding the reference to content. I'd recommend the data model
   require a per-record id within the stream and have the chain pointer
   carry both id and hash.

2. **Define genesis explicitly: the first record of a stream omits the
   previous-record pointer entirely — never a sentinel.** We shipped the
   sentinel version once (a literal `"GENESIS"` string inside a hash-valued
   field) and have it documented as an anti-pattern: a hash field whose
   value isn't a hash breaks every schema-driven verifier. One sentence of
   spec text here saves every implementer that round trip.

3. **Signatures and chain hashes are only third-party-verifiable if the
   record declares what bytes were hashed.** I'd recommend a required
   companion attribute naming the canonicalization for
   `audit.integrity.value` — RFC 8785/JCS, flat bytes, or a named producer
   scheme. OCSF landed on an enum plus a free-text sibling precisely so
   producers whose serialization isn't JCS can say so honestly instead of
   misclaiming; without it, "verify the signature" quietly becomes "trust
   the producer."

4. **Offer: a written OCSF↔OTel crosswalk.** The mappings look
   near-lossless from here — `audit.sequence.stream_id` ↔
   `attestation.chain_uid`, the producer/collector signer split ↔ producer
   signatures vs custody attestations with `authority_uid` naming the
   attesting party, the chain pointer ↔ `prev_event`. If we keep that
   mapping tight, one producer can emit both shapes (or transform between
   them) without divergent integrity constructs. Happy to draft it as a doc
   for the spec repo if useful.

We can also contribute test vectors for the verification-procedures
section: a production OCSF export (236-event chain, per-event ECDSA-P256
signatures verifiable against a public JWKS, no secrets required) and a
stdlib-only worked sample with fully recomputable fingerprints — both
public:

- https://github.com/levaj2000/ai-identity/tree/main/docs/cosai-ws4-ocsf-mapping/ocsf-log-reference-bundle
- https://github.com/levaj2000/ai-identity/tree/main/docs/cosai-ws4-ocsf-mapping/trust-base-inventory-sample

Looking forward to it.
