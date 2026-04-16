# Migrating flat RBAC policies to ABAC

**Audience:** operators running AI Identity with policies authored before the
ABAC release (commit `ce6d8358`).

**TL;DR:** flat RBAC policies keep working. 100% backward compatible. You
don't have to migrate anything. This guide is for teams that *want* to
tighten existing policies with metadata-driven conditions, incrementally and
safely.

---

## What changed

The policy engine used to evaluate rules of this shape only:

```yaml
allowed_endpoints: [...]
denied_endpoints:  [...]
allowed_methods:   [...]
```

After `ce6d8358` the engine also accepts an optional `when:` clause that
gates the rest of the rule on the agent's `metadata` dict:

```yaml
when:
  environment: "production"
  team:        {in: ["payments"]}
allowed_endpoints: [...]
```

If `when` is absent, behavior is **bit-for-bit identical** to the pre-ABAC
evaluator. (See `gateway/tests/test_enforce.py` — the legacy test suite
still passes against the new evaluator.)

## When should you migrate a policy?

Migrate a policy when you can answer yes to one of these:

1. **The policy today is broader than the real trust boundary.** For example,
   "all agents using this API key can hit `/v1/payments/*`" — but in reality
   only the payments team should, and you've been relying on key
   distribution as an out-of-band control.
2. **You want auditable deny reasons.** A flat policy denies with
   `allowed_endpoints:not_matched:<path>`. An ABAC policy can deny with
   `when:team:not_in:expected=['payments'],actual='sales'` — which is
   self-documenting evidence for a compliance reviewer.
3. **You're consolidating duplicated policies.** If you have three
   near-identical policies that differ only by which team gets which
   endpoint set, you can collapse them into one policy with a `when: team:`
   dispatch and fewer rows to keep in sync.

If none of those apply, leave the policy alone. ABAC is opt-in.

## Migration pattern (zero-change rollout)

The safe path is to migrate in three deploys, never widening access at any
step.

### Step 1 — Tag your agents (no policy change yet)

Add the metadata keys you plan to gate on to every existing agent, via the
agents admin API:

```bash
curl -X PATCH .../api/v1/agents/<agent_id> \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"metadata": {"environment": "production", "team": "payments"}}'
```

Nothing about policy evaluation changes yet — the engine just starts
storing the tags. Run for long enough to be confident every agent that
should match the future `when` clause has been tagged. A missing metadata
key fails the condition (fail-closed), so an un-tagged agent will be denied
the moment you ship Step 2.

> **Tip:** use the dry-run endpoint
> ([`POST /api/v1/policy/evaluate`](../../api/app/routers/policy_evaluate.py))
> with `{agent_id, endpoint, method}` to preview how the new policy would
> evaluate against the agent's *current* tags, before you enable it.

### Step 2 — Add `when` without removing fallback

Create a *new* policy with the `when` clause and activate it. Keep the old
flat policy deactivated but in the DB as a rollback target. If the new
policy denies something the old one allowed, you can swap back without
re-authoring.

### Step 3 — Retire the flat policy

Once the new policy has run for a full business cycle (a week is typical
for a cautious team) with no unexpected denies in the audit log, delete the
old policy. You're done.

## Concrete before / after

**Before — flat policy for a payment processor:**

```yaml
# policies table row — rules column
allowed_endpoints: [/v1/payments/*]
denied_endpoints:  [/v1/payments/admin/*]
allowed_methods:   [POST]
```

**After — same rules, now gated on agent metadata:**

```yaml
when:
  environment: "production"
  team:        {in: ["payments"]}
allowed_endpoints: [/v1/payments/*]
denied_endpoints:  [/v1/payments/admin/*]
allowed_methods:   [POST]
```

Effective access for a **correctly-tagged agent** is unchanged. What changes
is the *blast radius* of a stolen key or misconfigured agent: before, any
agent with this policy attached could call `/v1/payments/authorize`. After,
only production-environment, payments-team agents can.

## Failure modes to expect during migration

### "My policy is denying everything after I added `when`"

Almost always caused by **untagged agents**. Check the audit log — you'll
see rows like:

```
deny_reason = when:team:not_in:expected=['payments'],actual=None
```

`actual=None` means the metadata key wasn't set on the agent. Tag the
agent, or roll back to the flat policy.

### "Validation error: `depth exceeds maximum of 5`"

The `when` clause permits up to depth 5 (
`rules.when.<field>.<operator>.<list>.<scalar>`). If you exceed this,
you're almost certainly trying to express something the v1 DSL doesn't
support — nested objects, per-item conditions, or regex. File an issue; in
the meantime, flatten by computing the metadata tag at agent-creation time
rather than evaluating it at request time.

### "My policy saves but the dashboard shows yellow warnings"

`PolicyResponse` now includes a `warnings` array populated on policy
creation. A warning fires when the policy's `when` clause references a
metadata key that no currently-attached agent is tagged with — meaning the
policy will match *no* agents as written. This isn't an error (you may tag
agents next), just a nudge to double-check. See commit `ce6d8358` for the
full warning contract.

## Authoring conventions

These aren't enforced by the validator, but they're the conventions the
sample library uses and what pairs well with the dashboard's policy editor:

1. **One condition per line**, `when` block at the top. Humans read
   conditions before endpoints.
2. **Prefer `in` over chained equality**, even for a single value — it's
   trivial to add a second permitted value later without a diff that
   changes shape.
3. **Tag agents with 3–5 metadata keys max**: `environment`, `team`,
   `framework`, and maybe `cost_center` or `region`. More keys = more
   typo-driven denies in production.
4. **Never rely on missing-key semantics for access**. Tag every agent
   with every key the policy references, even if the value is
   `"unknown"`. The evaluator treats missing as fail-closed, but you want
   denies with readable `actual=<value>` strings, not `actual=None`.

## Reference

- Evaluator: [common/policy/eval.py](../../common/policy/eval.py)
- Validator: [common/validation/policy.py](../../common/validation/policy.py)
- Dry-run endpoint: [api/app/routers/policy_evaluate.py](../../api/app/routers/policy_evaluate.py)
- Sample library: [samples/](samples/)
- Evaluator tests (authoritative semantics): [common/tests/test_policy_eval.py](../../common/tests/test_policy_eval.py)
