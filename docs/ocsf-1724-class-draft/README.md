# OCSF Class Draft — AI Agent Trust Inventory (ocsf-schema#1724)

A PR-shaped draft of the Discovery class proposed in
[ocsf/ocsf-schema#1724](https://github.com/ocsf/ocsf-schema/issues/1724)
(@rabbidave), ready to hand to Dave the moment the co-drafting offer is taken
up. Files are laid out exactly as they would land in the `ocsf-schema` repo;
conventions were verified against `main` on 2026-08-11 (class-file shape from
`events/discovery/inventory_info.json` / `discovery.json`, profile attachment
from `events/base_event.json`, dictionary collisions checked by name).

**This is a draft for discussion, not a filed PR.** Class `uid`, attribute
names, and requirement levels are the working group's to assign; everything
here is a concrete starting point with the open questions called out.

---

## File map — where each file lands in ocsf-schema

| This directory | ocsf-schema destination |
|---|---|
| `events/discovery/ai_agent_trust_inventory.json` | `events/discovery/ai_agent_trust_inventory.json` |
| `objects/agent_config_declaration.json` | `objects/agent_config_declaration.json` |
| `objects/agent_execution_params.json` | `objects/agent_execution_params.json` |
| `objects/agent_artifact.json` | `objects/agent_artifact.json` |
| `objects/ai_sampling_params.json` | `objects/ai_sampling_params.json` |
| `objects/agent_credential.json` | `objects/agent_credential.json` |
| `dictionary-additions.json` | merged into `dictionary.json` `attributes` (it is a fragment, not a standalone file) |

Worked example events (shape-synced to this draft):
`../cosai-ws4-ocsf-mapping/trust-base-inventory-sample/`.

## Design decisions (and why)

1. **Thin class, fat objects.** The class adds four attributes
   (`actor`, `ai_agent`, `declared_configuration`, `executed_parameters`) and
   extends `discovery`, mirroring `inventory_info`'s minimalism. The
   declared/executed pairing — the issue's core semantic — lives in two
   objects so it can never be half-populated: both are `required`.
2. **`record_integrity` needs no registration.** The profile is attached at
   `base_event` (verified on `main`), so every class — including this one —
   already carries `attestation_list`. The per-emission chaining the issue
   asks for is purely a producer discipline; the class description states the
   instance-scoped `chain_uid` convention so the "gap in the chain =
   unrecorded change" property is normative-ish without schema mechanics.
3. **Charter rides `ai_agent.charter`.** The dictionary already types
   `charter` as a `file` object, and `file.hashes[]` carries fingerprints —
   so the charter digest has a native home with zero new attributes. The
   `agent_artifact` enum keeps `Charter (5)` only for producers whose charter
   is not carried on `ai_agent`.
4. **One artifact object + type enum**, not per-kind arrays
   (`adapters`/`tool_schema_sources`/`policy_bundles`). Fewer dictionary
   entries, one comparison rule for consumers, and OCSF's dictionary
   constrains each attribute name to one type globally — named per-kind
   arrays would burn five names to say what one enum says. `artifacts`
   appears in both declared and executed objects (same dictionary entry;
   the containing object provides the declared-vs-loaded meaning).
5. **Reused existing attributes everywhere possible.** `agent_artifact`
   introduces *no* new dictionary attributes (name, uid, version, type_id,
   type, fingerprint all exist — `fingerprint` from #1661). New entries are
   listed exhaustively in `dictionary-additions.json`; all were checked as
   absent from `dictionary.json` on 2026-08-11.
6. **Credentials are references by construction.** `agent_credential` has no
   field that could carry material; description text makes it normative.
   `Delegation Grant (4)` covers mandate/attenuable-token style credentials.
7. **Sampling parameters are config, not runtime state.** `ai_sampling_params`
   carries applied decoding config (the issue's "executed parameters")
   while the object description explicitly excludes activations/cache — the
   issue's non-goal, kept visible at the exact place someone would be
   tempted to violate it.
8. **Activity enum: Log / Collect / Change.** The class redefines
   `activity_id` fully (1/2 re-captioned from `discovery`, 3 added) —
   `Change` carries the admission-control timing contract in its
   description: *emitted after the change is observed and before the changed
   element executes*.
9. **`uid`: 24** — the lowest value above the highest currently assigned
   Discovery class (`cloud_resources_inventory_info` = 23). Entirely the
   maintainers' call; nothing downstream depends on it.

## Open questions to settle with Dave / the WG

1. **Class naming.** `ai_agent_trust_inventory` here; the category's naming
   pattern (`osint_inventory_info`, `cloud_resources_inventory_info`) argues
   for `ai_agent_inventory_info` — but that reads as *inventory of agents*,
   not inventory of one agent's trust base. Dave's issue title says
   "trust-base inventory"; keep his term unless the WG objects.
2. **Enum merge semantics.** Whether a subclass extends or replaces the
   parent's `activity_id` enum varies by tooling — the draft defines all
   three values to be safe; the compiled server output should be checked
   once it's in a real ocsf-schema clone (`ocsf-validator` + local server).
3. **Float attributes.** `temperature`/`top_p` are `float_t`. If the WG
   balks (float semantics in dictionaries have history), the fallback is
   string-typed values — lossless for audit purposes, uglier for analytics.
4. **`sampling` naming.** Possibly too generic for a global dictionary name;
   `ai_sampling` or folding the five scalars directly into
   `agent_execution_params` are both acceptable retreats.
5. **Should `executed_parameters.artifacts` be required when
   `declared_configuration.artifacts` is populated?** A constraint can't
   express cross-object conditions; today it's `optional` with the
   comparison semantics documented. Worth a WG opinion.
6. **TEE/workload attestation reference.** The issue's non-goal says
   *reference* hardware attestation rather than replace it. This draft adds
   no field for it — the separate workload-attestation gap (our issues
   draft #5, co-designed with the CMF side) is the right vehicle, and a
   `tee_quote`-style reference can be added to `agent_artifact` or the class
   later without breaking anything.

## Validation status

Checked here: every file parses as JSON; attribute references resolve either
to existing dictionary entries (verified by name against `main`) or to
`dictionary-additions.json`; enum/constraint shapes mirror merged files
(`ai_agent`, `agent_config_declaration`'s `at_least_one` follows #1661's
attestation constraint pattern). **Not** checked here: OCSF metaschema
validation — that requires the files sitting inside a real `ocsf-schema`
clone (`pip install ocsf-validator; python -m ocsf_validator .`), which is
the first step when this graduates from draft to PR branch.
