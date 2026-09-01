// Location: ./integrations/cpex-ocsf-audit/examples/panic_drive.rs
// Copyright 2026 AI Identity
// SPDX-License-Identifier: Apache-2.0
//
// Beat 06, driven for real.
//
// `demo_stream.rs` case 6 CONSTRUCTS a plugin_panic DecisionLog and hands
// it to the mapper. This one doesn't: it registers a plugin whose handler
// panics, runs it through the CPEX executor, and lets the seam produce the
// record. The panic is contained by the executor's `catch_unwind`, surfaces
// as `PluginError::Execution { code: "panic" }`, becomes a
// `plugin_panic` violation on a terminal deny (executor.rs, the
// `Ok(Err(e))` arm), and reaches this crate through the audit seam like any
// other verdict. Nothing about the record is written by hand.
//
// WHAT IS DIFFERENT ABOUT A REAL RECORD, and why it is not a defect:
//
// The executor owns the decision stream's identity. `stream_id` is the
// literal "decision" (executor.rs `stamp_decision_stream`) and `epoch` is
// the executor's boot time in Unix nanoseconds, captured in `Executor::new`
// with no setter. So this record does NOT join the demo's synthetic
// `gw-1/boot-7` stream, and its epoch changes on every run.
//
// That is the honest cost of the record being real, and the alternative was
// never on the table: the stream stamps ride INSIDE the hashed bytes, so
// rewriting them to match the synthetic stream would be forging the
// evidence — the exact failure this crate exists to make detectable.
//
// What does carry across, and is what the ledger side correlates on:
// `ai_agent.uid` and `metadata.correlation_uid` come from the
// AgentExtension supplied here, not from the executor's stamping. So a real
// beat 06 still names agent-7 and still joins the run.
//
//   DEMO_SIGNING_KEY  PKCS#8 P-256 PEM path; when set, chain + DSSE
//   DEMO_KEY_ID       JWKS kid stamped on the record
//   DEMO_AUTHORITY    attestation authority_uid
//   DEMO_CHAIN_UID    attestation chain uid
//   DEMO_AGENT_ID     ai_agent.uid              (default "agent-7")
//   DEMO_CONVERSATION_ID
//                     run id -> metadata.correlation_uid
//                                               (default "run-4bf92f35")
//   DEMO_SESSION_ID   ai_agent.instance_uid     (default "sess-gw-1-boot-7")
//
// The record is emitted by the configured OCSF destination, which is
// stderr — so a runner collects it with `2>`, keeping it off the stdout
// NDJSON of the synthetic beats.
//
//   cargo run --example panic_drive 2>beat06.ndjson

use std::collections::HashMap;
use std::sync::Arc;

use serde_json::json;

use cpex_plugin_ocsf_audit::OcsfAuditEmitter;

use cpex_core::cmf::{ContentPart, CmfHook, Message, MessagePayload, Role, ToolCall};
use cpex_core::executor::{Executor, ExecutorConfig};
use cpex_core::extensions::{
    AgentExtension, Extensions, SecurityExtension, SubjectExtension,
};
use cpex_core::hooks::adapter::TypedHandlerAdapter;
use cpex_core::hooks::trait_def::{HookHandler, PluginResult};
use cpex_core::context::PluginContext;
use cpex_core::plugin::{OnError, Plugin, PluginConfig, PluginMode};
use cpex_core::registry::{AnyHookHandler, HookEntry, PluginRef};

fn env_str(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

/// A plugin that panics. That is the whole point of it.
///
/// Sequential mode with `on_error: Fail` is what makes the panic terminal:
/// the executor's blocking branch turns a contained panic into a
/// `plugin_panic` violation and denies. In a non-blocking phase the same
/// panic would be recorded as an error and the request would continue,
/// which is a different (also real) behaviour and not the one beat 06 is
/// about.
struct PanickingPlugin {
    cfg: PluginConfig,
}

impl Plugin for PanickingPlugin {
    fn config(&self) -> &PluginConfig {
        &self.cfg
    }
}

impl HookHandler<CmfHook> for PanickingPlugin {
    async fn handle(
        &self,
        _payload: &MessagePayload,
        _ext: &Extensions,
        _ctx: &mut PluginContext,
    ) -> PluginResult<MessagePayload> {
        // Not `PluginResult::deny(...)` — that would be an orderly refusal,
        // which beats 03 and 04 already cover. This is the ungraceful case:
        // the plugin comes apart mid-decision and the platform has to hold
        // the line without its cooperation.
        panic!("simulated mint failure");
    }
}

fn sink() -> Arc<OcsfAuditEmitter> {
    let mut cfg = json!({
        "chain": false,
        "product_name": "AI Identity OCSF Audit",
        "vendor_name": "AI Identity",
    });

    if let Ok(key_path) = std::env::var("DEMO_SIGNING_KEY") {
        cfg["chain"] = json!(true);
        cfg["signing"] = json!("dsse");
        cfg["signing_key_pem_path"] = json!(key_path);
        cfg["signing_key_id"] = json!(env_str("DEMO_KEY_ID", "demo-key-2026-08"));
        cfg["authority_uid"] = json!(env_str("DEMO_AUTHORITY", "org-f3576cf6"));
        cfg["chain_uid"] = json!(env_str("DEMO_CHAIN_UID", "demo-chain-boot-7-e3"));
    }

    // No `hooks:` — audit-only sink mode, which is what attaches this as an
    // AuditHandler rather than a post-hook observer. A post-hook observer
    // would never see this record: the request is denied, so it never
    // reaches a post hook. That asymmetry is the reason the audit seam
    // exists.
    let config = PluginConfig {
        name: "ocsf-decision-sink-demo".into(),
        kind: "audit/ocsf".into(),
        hooks: vec![],
        mode: PluginMode::Audit,
        priority: 50,
        on_error: OnError::Fail,
        config: Some(cfg),
        ..Default::default()
    };
    Arc::new(OcsfAuditEmitter::new(config).expect("valid demo config"))
}

fn request() -> (MessagePayload, Extensions) {
    let payload = MessagePayload {
        message: Message::with_content(
            Role::Tool,
            vec![ContentPart::ToolCall {
                content: ToolCall {
                    tool_call_id: "call-042".into(),
                    name: "get_compensation".into(),
                    arguments: HashMap::from([("employee_id".to_string(), json!("EMP-001234"))]),
                    namespace: Some("hr".into()),
                },
            }],
        ),
    };

    let mut sec = SecurityExtension::default();
    let mut subj = SubjectExtension::default();
    subj.id = Some("alice@corp.com".into());
    subj.roles.insert("hr".into());
    sec.subject = Some(subj);
    sec.labels.insert("PII".into());

    // Same agent and run as the synthetic beats. These are what survive the
    // executor's own stream stamping, so a real beat 06 still correlates
    // with beats 01-05 on the ledger side.
    let agent = AgentExtension {
        agent_id: Some(env_str("DEMO_AGENT_ID", "agent-7")),
        conversation_id: Some(env_str("DEMO_CONVERSATION_ID", "run-4bf92f35")),
        session_id: Some(env_str("DEMO_SESSION_ID", "sess-gw-1-boot-7")),
        ..Default::default()
    };

    (
        payload,
        Extensions {
            security: Some(Arc::new(sec)),
            agent: Some(Arc::new(agent)),
            ..Default::default()
        },
    )
}

#[tokio::main(flavor = "current_thread")]
async fn main() {
    let emitter = sink();

    let plugin_cfg = PluginConfig {
        name: "minter".into(),
        kind: "demo/panicking".into(),
        hooks: vec!["cmf.tool_pre_invoke".into()],
        mode: PluginMode::Sequential,
        priority: 10,
        on_error: OnError::Fail,
        ..Default::default()
    };

    let panicker = Arc::new(PanickingPlugin {
        cfg: plugin_cfg.clone(),
    });
    let plugin_ref = Arc::new(PluginRef::new(
        panicker.clone() as Arc<dyn Plugin>,
        plugin_cfg,
    ));
    let handler: Arc<dyn AnyHookHandler> =
        Arc::new(TypedHandlerAdapter::<CmfHook, _>::new(panicker));
    let entry = HookEntry {
        plugin_ref,
        handler,
    };

    let mut executor = Executor::new(ExecutorConfig::default());
    executor.push_audit_handler(emitter);

    let (payload, ext) = request();
    let tracker = tokio_util::task::TaskTracker::new();

    let (result, _bg) = executor
        .execute(&[entry], Box::new(payload), ext, None, &tracker)
        .await;

    // The record has already been emitted by the audit seam at this point.
    // Assert the shape the demo claims, so a silent behaviour change
    // upstream fails here rather than on stage.
    assert!(
        result.is_denied(),
        "a panicking sequential plugin with on_error=fail must deny"
    );
    let violation = match result.decision_log.verdict() {
        Some(cpex_core::decision::Verdict::Deny(v)) => v,
        other => panic!("expected a deny verdict, got {other:?}"),
    };
    assert_eq!(
        violation.code, "plugin_panic",
        "a contained panic must surface as plugin_panic, not plugin_error"
    );
    assert_eq!(violation.plugin_name.as_deref(), Some("minter"));

    eprintln!(
        "// verify: real panic driven — verdict deny, violation {}, plugin {}",
        violation.code,
        violation.plugin_name.as_deref().unwrap_or("?"),
    );
}
