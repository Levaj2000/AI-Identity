// Location: ./integrations/cpex-ocsf-audit/src/lib.rs
// Copyright 2026 AI Identity
// SPDX-License-Identifier: Apache-2.0
//
// cpex-plugin-ocsf-audit — CMF plugin that emits one OCSF AI Operation
// event per dispatched request, off the CPEX `run(audit-log)` seam.
//
// It is a near-twin of the upstream `audit-logger` builtin (same
// observation-only, always-allow contract, same factory + hook wiring).
// The difference is the record shape: instead of a free-form JSON line,
// it serializes the CMF `Message` + `Extensions` into an OCSF event,
// following docs/cosai-ws4-ocsf-mapping/CMF-OCSF-FIELD-MAP.md, then
// (optionally) attaches a tamper-evident attestation chain
// (fingerprint → prev_event.fingerprint) and signs it.
//
// Why this exists: it makes CPEX's enforcement record interoperable
// (OCSF) and independently verifiable (signed attestation chain),
// without CPEX having to own a schema. CPEX produces the event; this
// plugin makes it portable and verifiable offline.
//
// CMF = ContextForge Message Format (per cpex-core/src/cmf/mod.rs).
//
// Status: builds green against cpex@feat/hil_apl `ad666ba` (cargo build
// + cargo test; Teryl's review baseline, 2026-07-06). The Extension
// field reads and ContentPart variant shapes are confirmed against that
// commit. Review corrections applied 2026-07-06 (see
// docs/cosai-ws4-ocsf-mapping/cmf-ocsf-mapping-review.md): prompt hooks
// register on cmf.prompt_*_invoke (C6 — the _fetch names silently never
// fire), correlation_uid mirrors the run id (C1), and events are
// JCS-style canonically serialized so the fingerprint chain verifies
// independently (C2 caveat).
//
// Revision 2026-07-20 (P0 + review §4-B, per the production-readiness
// plan agreed 2026-07-17/18): host class is now API Activity (6003) with
// its real activity enum (CRUD via readOnlyHint, else 99 + source name);
// metadata.profiles declares ai_operation + security_control (+
// record_integrity when chained) and the passive stream carries
// action_id 3 (Observed) / disposition_id 17 (Logged); and the hash
// commits to the record's chain position — predecessor binding, not a
// back-pointer. (The deny/modify records this note deferred to WS-A /
// P1 landed 2026-08-18 — see the decision-sink revision below.)
//
// Revision 2026-07-31 — MERGED #1661 SHAPE. PR #1661 merged upstream
// 2026-07-17 (`2a244bc9`), and the emitted attestation now matches it:
// `attestation_list[]` carrying `fingerprint` / `prev_event` /
// `signatures` objects, replacing the draft `attestation` member with
// string `entry_hash` / `prev_entry_hash` / singular `signature`. The
// fingerprint is computed per the merged semantics — over the whole
// event including the attestation's own uid/chain_uid/prev_event and
// excluding only fingerprint/signatures — so a verifier following the
// schema can reproduce it without knowing anything about this crate.
// `metadata.uid` is now emitted (prev_event references point at it) and
// `correlation_uid` moved to `metadata`, which is where OCSF defines
// it. Signature bytes ride in `unmapped.signature_b64` pending
// ocsf-schema#1709.
//
// Revision 2026-07-31 (same day, later) — SIGNER WIRED + authority_uid.
// `sign::DsseSigner` is real: ECDSA-P256-SHA256 over the DSSE PAE of
// the fingerprint's canonical bytes (RFC 6979 deterministic), key
// operator-provided as PKCS#8 PEM, loud config failure when missing.
// `attestation.authority_uid` (recommended in the merged schema) names
// the party the signing credential belongs to and sits INSIDE the
// hashed bytes. Verifier rule is running code: `sign::signing_input` +
// `sign::dsse_pae`. Key custody (HSM/KMS, rotation epochs, JWKS
// publication) is deliberately out of plugin scope — it belongs to the
// operating authority.
//
// Revision 2026-08-18 — DECISION-AUDIT SINK (WS-A / P1 delivered). The
// plugin now consumes the first-class audit seam from cpex PR #166
// (verified against feat/audit-seam @ 386710a, post-hardening): with no
// `hooks:` listed it auto-attaches as an AuditHandler
// (Plugin::as_audit_handler) and fires at every pipeline verdict —
// denials included, which the post-hook path structurally never saw.
// The DecisionLog maps as: verdict -> security_control (Deny -> action 2
// Denied / disposition 2 Blocked, violation at status_code/status_detail
// so `plugin_panic` survives by code; Allow-after-modification ->
// action 4 Modified; plain Allow -> 1/1), and the ordered per-plugin
// steps (full vocabulary incl. deny_ignored / aborted), span, entry
// taint, content hashes and the (epoch, stream_id, stream_seq,
// emission_seq) stamps ride under unmapped.cpex.* — inside the hashed
// bytes, so the decision facts are tamper-evident in the attestation
// chain. Listing hooks still runs the legacy post-hook observer (and
// then deliberately does NOT also attach, so one invocation never emits
// twice). Effect-lifecycle events (AuditHandler::on_effect) are the
// next tracked step — a token mint wants a richer OCSF class than 6003.

// Revision 2026-09-07 — HOST FEATURE (the praxis port, PRAXIS-PORT-RESULTS.md).
// The seam this crate consumes now exists on two engines: cpex PR #166
// and praxis-proxy/policy PR #84, Teryl's port of it into the Praxis
// Policy Engine. Exactly one is selected per build by the `cpex`
// (default) / `ppe` feature, and every engine type this crate names is
// reached through `crate::host::…` so the source has one import root.
// The seam API is line-for-line the same on both (AuditHandler,
// DecisionLog, the step vocabulary, the stream stamps) and the emitted
// records are byte-identical. The one shape difference — PPE binds the
// violation to a Denied / DenyIgnored step, cpex leaves it on the
// verdict — is absorbed by the three helpers in `host`, nowhere else.

#[cfg(all(feature = "cpex", feature = "ppe"))]
compile_error!(
    "features `cpex` and `ppe` select the host engine and are mutually exclusive: \
     build the praxis port with `--no-default-features --features ppe`"
);
#[cfg(not(any(feature = "cpex", feature = "ppe")))]
compile_error!("one host feature is required: `cpex` (the default) or `ppe`");

/// The policy engine this build targets, re-exported under one name.
///
/// `host::decision`, `host::cmf`, `host::plugin`, … are the engine's own
/// modules — `cpex_core` under the `cpex` feature, `praxis_policy_core`
/// under `ppe`. The module tree is the same on both, which is why one
/// alias is enough.
pub mod host {
    #[cfg(feature = "cpex")]
    pub use cpex_core::*;
    #[cfg(feature = "ppe")]
    pub use praxis_policy_core::*;

    use self::decision::PluginAction;
    use self::error::PluginViolation;

    /// The engine this build consumes, for logs and results docs. Not a
    /// wire value: the `cpex.*` / `cmf.*` record prefixes are pinned by
    /// AID-EMIT-1 and do not follow the engine.
    #[cfg(feature = "cpex")]
    pub const ENGINE: &str = "cpex";
    #[cfg(feature = "ppe")]
    pub const ENGINE: &str = "praxis-policy-core";

    /// A step that denied. On PPE (PR #84 `7da262d`) the step carries
    /// its violation; on cpex the verdict does and the step is a unit
    /// variant, so the violation is dropped here — the verdict still
    /// names it at `status_code` / `status_detail`.
    pub fn denied(violation: PluginViolation) -> PluginAction {
        #[cfg(feature = "cpex")]
        {
            let _ = violation;
            PluginAction::Denied
        }
        #[cfg(feature = "ppe")]
        {
            PluginAction::Denied(Box::new(violation))
        }
    }

    /// A step that asked to deny from a phase that cannot block and was
    /// overruled. Same shape split as [`denied`]; on PPE this is the
    /// only place the objection survives, since no verdict names it.
    pub fn deny_ignored(violation: PluginViolation) -> PluginAction {
        #[cfg(feature = "cpex")]
        {
            let _ = violation;
            PluginAction::DenyIgnored
        }
        #[cfg(feature = "ppe")]
        {
            PluginAction::DenyIgnored(Box::new(violation))
        }
    }

    /// Whether a step is a suppressed deny, whichever shape the host
    /// gives the variant.
    pub fn is_deny_ignored(action: &PluginAction) -> bool {
        #[cfg(feature = "cpex")]
        {
            *action == PluginAction::DenyIgnored
        }
        #[cfg(feature = "ppe")]
        {
            matches!(action, PluginAction::DenyIgnored(_))
        }
    }
}

pub mod config;
pub mod emitter;
pub mod factory;
pub mod ocsf;
pub mod sign;

pub use config::{OcsfAuditConfig, OcsfDestination, SigningMode};
pub use emitter::OcsfAuditEmitter;
pub use factory::{OcsfAuditFactory, KIND};
