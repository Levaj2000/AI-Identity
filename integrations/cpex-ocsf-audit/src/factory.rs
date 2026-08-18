// Location: ./integrations/cpex-ocsf-audit/src/factory.rs
// Copyright 2026 AI Identity
// SPDX-License-Identifier: Apache-2.0
//
// Factory — registers the emitter under every CMF hook the operator
// lists in `hooks:`. Structurally identical to the upstream
// audit-logger factory (TypedHandlerAdapter<CmfHook, _> per hook name).

use std::sync::Arc;

use cpex_core::{
    cmf::CmfHook,
    error::PluginError,
    factory::{PluginFactory, PluginInstance},
    hooks::TypedHandlerAdapter,
    plugin::PluginConfig,
};

use crate::emitter::OcsfAuditEmitter;

/// `kind:` string operators write in CPEX YAML to declare an OCSF
/// audit emitter instance.
pub const KIND: &str = "audit/ocsf";

pub struct OcsfAuditFactory;

impl PluginFactory for OcsfAuditFactory {
    fn create(&self, config: &PluginConfig) -> Result<PluginInstance, Box<PluginError>> {
        let emitter = Arc::new(OcsfAuditEmitter::new(config.clone())?);

        // Make the inferred mode explicit in the startup log (mirrors the
        // upstream audit-logger factory): audit-only sink is the
        // recommended mode, but an operator who *meant* to list hooks and
        // lost them to a YAML slip should be able to catch it here.
        if config.hooks.is_empty() {
            // Audit-only sink mode: no CMF post-hook handlers; the plugin
            // auto-attaches as a decision-audit sink instead (see
            // `Plugin::as_audit_handler` in emitter.rs) and fires at every
            // pipeline verdict — denials included. This is the recommended
            // mode on cpex with the audit seam (PR #166).
            tracing::info!(
                plugin = %config.name,
                "ocsf-audit '{}' running in audit-only sink mode (no `hooks:` listed) — \
                 auto-attaches to the executor verdict path; if you meant to observe \
                 specific CMF hooks, list them under `hooks:`",
                config.name,
            );
            return Ok(PluginInstance {
                plugin: emitter,
                handlers: Vec::new(),
            });
        }
        tracing::info!(
            plugin = %config.name,
            hooks = ?config.hooks,
            "ocsf-audit '{}' running as a CMF post-hook observer on {:?} — this path \
             sees allowed traffic only; audit-only sink mode (no `hooks:`) also \
             records denials. (Avoid cmf.prompt_post_fetch — the runtime dispatches \
             cmf.prompt_post_invoke; a handler on the _fetch name silently never fires.)",
            config.name,
            config.hooks,
        );

        let handlers: Vec<_> = config
            .hooks
            .iter()
            .map(|h| -> (&'static str, _) {
                let leaked: &'static str = Box::leak(h.clone().into_boxed_str());
                let adapter: Arc<dyn cpex_core::registry::AnyHookHandler> =
                    Arc::new(TypedHandlerAdapter::<CmfHook, _>::new(Arc::clone(&emitter)));
                (leaked, adapter)
            })
            .collect();

        Ok(PluginInstance {
            plugin: emitter,
            handlers,
        })
    }
}
