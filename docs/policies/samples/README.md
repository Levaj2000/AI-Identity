# Sample Policy Library

A reference library of working AI Identity policies, ordered from simplest
to most complete. Every sample is a copy-pasteable starting point — drop the
`rules:` block into the `rules` JSONB column of a `policies` row (or the
`rules` field of the dry-run endpoint) and it will evaluate exactly as the
comments describe.

Each file includes:

- A **use case** — the real-world scenario this shape fits.
- The **DSL feature** it demonstrates.
- **Example pass / deny** cases with the exact `deny_reason` string the
  evaluator emits, so you can predict audit-log output before you ship.

## Index

| # | File | DSL features | Fits |
|---|------|--------------|------|
| 01 | [01-read-only-rbac.yaml](01-read-only-rbac.yaml) | flat RBAC (no `when`) | simple read agents |
| 02 | [02-production-only.yaml](02-production-only.yaml) | equality shorthand | prod-only endpoints |
| 03 | [03-team-scoped-payments.yaml](03-team-scoped-payments.yaml) | `in` operator | team-scoped access |
| 04 | [04-exclude-test-frameworks.yaml](04-exclude-test-frameworks.yaml) | `not_in` operator | block test harnesses |
| 05 | [05-prod-payments-combined.yaml](05-prod-payments-combined.yaml) | multi-condition AND | prod + team crossover |
| 06 | [06-compliance-deny-admin.yaml](06-compliance-deny-admin.yaml) | `denied_endpoints` | SOC 2 boundary enforcement |
| 07 | [07-method-scoped-read.yaml](07-method-scoped-read.yaml) | `allowed_methods` | read-only integrations |
| 08 | [08-full-stack-prod-write.yaml](08-full-stack-prod-write.yaml) | all features combined | production design-partner baseline |

## DSL quick reference

```yaml
when:                                       # optional — implicit AND across keys
  environment: "production"                 # scalar = equality
  team:        {in:     ["payments"]}       # IN
  framework:   {not_in: ["pytest"]}         # NOT IN
allowed_endpoints:                          # required for any allow
  - /v1/*                                   # prefix wildcard
  - /v1/specific/endpoint                   # exact match
  - "*"                                     # full wildcard
denied_endpoints:                           # optional — checked first, wins
  - /v1/admin/*
allowed_methods:                            # optional — empty = any method
  - POST
```

### Evaluation order

1. `when` — every condition must pass. A missing metadata key fails the
   condition (fail-closed).
2. `denied_endpoints` — explicit denies fire before the allow list.
3. `allowed_endpoints` — at least one pattern must match.
4. `allowed_methods` — if set, method must be in the list.

### Values allowed in metadata comparisons

Scalars only: `string | int | float | bool`. No lists, dicts, or regex on
the agent-metadata side in v1. If you need set membership, put the set on
the policy side with `in` / `not_in`.

### Fail-closed guarantees

- Missing `when` key on the agent → condition fails → request denied.
- Malformed rules or unknown operators → denied with a stable `deny_reason`.
- Empty `allowed_endpoints` → denied (`allowed_endpoints:not_configured`).

## Validating a sample before you ship it

Use the dry-run endpoint ([api/app/routers/policy_evaluate.py](../../../api/app/routers/policy_evaluate.py))
to confirm behavior without touching production:

```bash
curl -X POST https://<api>/api/v1/policy/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "rules": { "when": {"team": {"in": ["payments"]}},
                   "allowed_endpoints": ["/v1/payments/*"],
                   "allowed_methods": ["POST"] },
        "agent_metadata": {"team": "sales"},
        "endpoint": "/v1/payments/authorize",
        "method": "POST"
      }'
```

Response includes the full per-condition trace (`when_conditions`) so you
can debug what would have matched and what wouldn't.

## Migrating existing policies

See [../migration-rbac-to-abac.md](../migration-rbac-to-abac.md) — a
before/after walkthrough for adding `when` clauses to flat policies without
changing any agent's effective permissions.
