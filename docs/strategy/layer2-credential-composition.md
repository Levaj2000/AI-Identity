# Mandate Credentials at Layer 2: What Composes, and Where the Counter Lives

**Status:** discussion note, not a proposal. Companion to the
[WS4 interop map](./cosai-ws4-interop-map.md) and to the field-level fit table
between Verifiable Intent's L2 credential and the CMF delegation extension.
Written because "is format A a replacement for format B" keeps coming up, and
the answer turns out to depend on a distinction that neither format states.

**Pinned inputs** (claims about a moving target are worthless without one):

| Side | Source | Revision |
|---|---|---|
| Verifiable Intent | `agent-intent/verifiable-intent`, `spec/credential-format.md` 4.2-4.7 and `spec/constraints.md` | `main`, Apache-2.0, draft v0.1, read 2026-09-10 |
| Biscuit | `biscuit-auth`, as minted and verified in `common/biscuit/tokens.py` | this repository, 0.4.0 onward |
| Mandate document | `mandate/app/schemas.py`, `mandate/app/constraints.py`, schema 1.2 | this repository |
| CMF delegation | read from the sink, `integrations/cpex-ocsf-audit/src/ocsf.rs` | plugin pin |
| OCSF `delegation` | `ocsf-schema`, four attributes, all correlation identifiers | 1.9.0 |

Everything said about VI here is read from the spec at that revision, from the
outside. Corrections from its owners beat this document.

---

## 1. Four roles, one word

"Mandate" gets used for four different things, and most format arguments are
really arguments about which of the four is under discussion:

1. **The grant.** The authoritative, signed statement of terms: who may act
   for whom, within what bounds, until when.
2. **The presentation.** What the agent actually shows an enforcement point.
   It may be the grant itself, or a narrowed view of it.
3. **The counter.** Consumption against the grant. Mutable, and it needs a
   single writer.
4. **The receipt.** Signed evidence handed back after the authority was used
   or refused, so the delegator learns what its delegate did without
   instrumenting the delegate.

A credential format can supply roles 1 and 2. No credential format supplies
role 3, and only an issuer or enforcement point can supply role 4. That is the
whole answer to "does this replace that": two credential formats compete for
roles 1 and 2 and are silent on the rest.

## 2. What each format actually supplies

| | VI L2 | Biscuit | Mandate document (this repo) |
|---|---|---|---|
| Wire format | SD-JWT (JWS + selective disclosure) | Ed25519-signed Datalog blocks | ECDSA-signed JSON, RFC 8785 canonical |
| Holder binding | Yes, RFC 7800 `cnf` on the credential | No, bearer. The subject check binds a claimed identity the verifier asserts | N/A, not presented directly |
| Narrowing after issue | Not that the spec shows: issuance-time | Yes, offline attenuation, append-only | N/A |
| Bounds vocabulary | Registered, typed, quantitative | Whatever Datalog facts both ends agreed on | Namespaced types, `mandate/app/constraints.py` |
| Selective disclosure | Yes | No | No |
| Holds the counter | No | No | No, the service does |
| Verification needs network | No | No | No, but settlement does |

The bearer note on Biscuit is not a criticism from outside; it is the honesty
note in our own minting module. A Biscuit's `subject` check binds the token to
a claimed agent identity, but it is the gateway that asserts which identity was
presented, so real possession binding needs the gateway to authenticate the
agent independently.

Read the columns as capability sets rather than scores. VI has the binding and
the vocabulary and no attenuation story. Biscuit has attenuation and no binding
and no shared vocabulary. They are close to complements.

## 3. The stateless line runs through the vocabulary, not around it

Verification is a pure function of the credential and the clock. That splits
the bounds a grant can express into two classes, and the split does not respect
the boundary between formats:

| Bound | Decidable from credential plus the request | Needs a counter |
|---|---|---|
| Expiry | Yes | |
| Per-transaction amount range | Yes | |
| Payee or merchant allowlist | Yes | |
| Scope or action class | Yes | |
| Cumulative budget over the grant's life | | Yes |
| Recurrence, "once per period" | | Yes |
| Line-item quantities drawn across calls | | Yes |
| Revocation | | Yes |
| Replay (`nonce`, `jti`) | | Yes |

A credential can state a cumulative ceiling. It cannot know what has been spent
against it. So the second column is not an implementation detail one format got
wrong: it is outside what any signed artifact can decide, and it belongs to
whatever holds the writer.

Which means choosing between credential formats is choosing a presentation, not
an architecture. Two deployments can agree on the format and still disagree
about what a grant permits, because the disagreement lives in the counter.

## 4. Monotonic narrowing: the property a chain needs and nobody states

If authority moves down a chain, the property that makes the chain checkable is
that no hop can hold more than its parent granted. For any hop `n`,
`bounds(n)` must be a subset of `bounds(n-1)`.

Where the four representations stand:

- **Biscuit** enforces it structurally. Attenuation appends blocks, and every
  block's checks must pass, so an added check can only narrow. A delegate
  cannot widen its own token even offline, which is the point of the design.
- **VI** does not appear to offer narrowing at all after issuance. L3 splits
  the network-facing and merchant-facing views, but that is a split at issue
  time, not a delegate tightening its own ceiling. Worth confirming with the
  spec owners rather than assuming.
- **A CMF delegation chain** can represent narrowing, since `scopes_granted`
  is per hop, but nothing makes it monotonic. A hop listing more scopes than
  its parent produces a record that looks exactly like a valid one.
- **OCSF's `delegation`** cannot express bounds at all, so the question does
  not arise yet. It would arise the moment a terms field lands.

This is cheap to state and checkable in a record after the fact, which is
unusual for a security property. It is a candidate for the shortest useful
thing a record layer could say about a delegation chain beyond its shape.

## 5. Two rules that survive whichever format wins

**One bound, one encoding.** A bound written in two places will eventually be
written two ways. This is already enforced inside our own document:
`spend.ceiling` is registered in the constraint vocabulary and refused inside
`constraints[]`, because `spend_limit` is its one encoding. The same rule
applies across formats: if a credential is carried inside a delegation hop and
the hop restates the ceiling, the two copies are a drift bug waiting to be
found by a reconciliation nobody wrote. Carry a reference and a hash instead,
and dereference for the terms.

**A bound nobody evaluates must deny.** Registered is not the same as
evaluable. Our registry names a type only as a promise that something can check
it, and a type with no evaluator behind it denies at enforcement rather than
passing, under an explicit reason code. The cross-format version matters more
than the internal one: when a credential in format A is carried through
representation B and consumed by an enforcement point that cannot evaluate A's
constraint types, treating those constraints as absent widens authority past
what the issuer signed. That is the most likely way a composition of two
correct systems produces an incorrect one, and it is silent when it happens.

## 6. How they compose in a stack that runs

This is not hypothetical layering; it is the arrangement already in this
repository, and it is what makes the "replacement" question answerable:

1. **Grant.** The ECDSA-signed mandate document is authoritative. Its terms
   are signed; unknown fields and unevaluable conditions fail closed.
2. **Presentation.** A Biscuit is minted from that grant's terms as a
   presentation credential, not as the grant. The ceiling travels inside the
   token as a check, so a widened cap fails cryptographically rather than by
   lookup.
3. **Verification.** The enforcement point verifies offline against the
   published root public key: signature, attenuation chain, expiry, audience,
   scopes, and the token's embedded checks. No network call to authorize.
4. **Settlement.** Spend-bearing calls settle the draw against the mandate
   service, the single writer for cumulative state. It applies the grant's
   signed conditions before mutating, using the same evaluator as a policy
   `when` clause, so a missing key is a failed match rather than a pass.
5. **Receipt.** The service mints an Ed25519 signed receipt over the RFC 8785
   canonicalization, anchored to the same root key that anchors the tokens, so
   one published key verifies authority downstream and evidence upstream. The
   receipt carries a correlation id back to the chained audit rows and a
   revocation id identifying which copy of the authority acted.
6. **Record.** The decision and its context serialize into signed OCSF events.

Step 2 is a slot. Putting a VI L2 credential in it changes the presentation
format and the binding story, and changes nothing about steps 1, 3, 4, 5 or 6.
That is the test for whether two formats are alternatives: if one of them is a
slot in a working arrangement, it is a slot, not an architecture.

Two enforcement modes exist at step 4 and the distinction is worth carrying
into any shared model. In `enforce`, a draw that would cross the ceiling is
denied and not recorded, so the remaining budget is untouched: prevention. In
`settlement`, the money already moved through an out-of-band channel, the draw
is recorded even though it crosses, and the crossing moves the grant to a
terminal exceeded state: detection. A record layer that models only the first
cannot represent what actually happened in the second.

## 7. What nobody models yet

Two gaps, one filed and one not.

**Consumption.** OCSF's `delegation` object carries four attributes and all
four are correlation identifiers, so a record can say a grant existed, who
issued it, and its ancestry, but not what it permitted or how much of it was
used. Filed as [ocsf#1756](https://github.com/ocsf/ocsf-schema/issues/1756),
proposing a constraint object covering both a grant's terms and the consumption
against them. The terms half is re-derivable from the credential. The
consumption half exists only at the enforcement point, and if it is not in the
record, a later reader cannot tell whether a grant with a 50000 ceiling had
49900 remaining or 100 when the agent acted.

**Receipts.** The evidence that flows back to the delegator has no proposal
anywhere that we have found. A grant, the consumption against it, and a receipt
the delegator can verify offline are one loop; the industry has specified the
first third of it, is in the middle of the second, and has not started the
third.

## 8. Open questions

For the owners of the representations involved, not assertions about them:

1. Does VI support narrowing after issuance by the holder, or is every
   narrower authority a new credential from the issuer?
2. In a delegation chain representation, is monotonic narrowing across hops
   asserted, enforced, or neither?
3. Is a hop's TTL anchored to the credential's own issued-at or to the moment
   the carrier observed it? Those differ by the ingestion delay, so two
   identical grants expire at different moments depending on when each was
   seen.
4. Would a delegation hop accept a key-binding field and a typed constraint
   list, given a field that survives deleting the payments context is the test
   for whether it belongs in a general model?
5. Where should the consumption counter be recorded when two enforcement
   points share one grant?
