// Location: ./integrations/cpex-ocsf-audit/examples/decision_sink_demo.rs
// Copyright 2026 AI Identity
// SPDX-License-Identifier: Apache-2.0
//
// Demo: the decision-audit sink — the half of this plugin that consumes
// the cpex#166 audit seam. A sink-mode emitter (no `hooks:` listed, so
// it attaches as an `AuditHandler`) receives the executor's finalized
// `DecisionLog` at every pipeline verdict and turns it into an OCSF
// event. This example feeds it the four rulings that matter and
// pretty-prints what lands in the audit stream:
//
//   1. Allow                — every plugin let the request through
//   2. Allow-after-modify   — a redactor rewrote the payload (Modified)
//   3. Deny                 — the PDP blocked it (violation -> status)
//   4. Suppressed deny      — a Transform-phase plugin signalled deny and
//                             was ignored by role (`deny_ignored`), plus a
//                             concurrent branch cancelled (`aborted`).
//                             Terminal verdict Allow — the record a
//                             post-hook observer could never produce.
//
//   cargo run --example decision_sink_demo
//
// Timestamps and stream stamps are fixed so the output is deterministic.

use std::collections::HashMap;
use std::sync::Arc;

use serde_json::json;

use cpex_plugin_ocsf_audit::OcsfAuditEmitter;

use cpex_core::cmf::{ContentPart, Message, MessagePayload, Role, ToolCall};
use cpex_core::decision::{DecisionLog, PluginAction, Span, Verdict};
use cpex_core::error::PluginViolation;
use cpex_core::extensions::{Extensions, SecurityExtension, SubjectExtension};
use cpex_core::plugin::{OnError, PluginConfig, PluginMode};

/// Sink-mode emitter: `hooks` is EMPTY, which is what makes the factory
/// attach this instance as a decision-audit sink (`as_audit_handler()`)
/// instead of a post-hook observer.
fn sink() -> OcsfAuditEmitter {
    let config = PluginConfig {
        name: "ocsf-decision-sink-demo".into(),
        kind: "audit/ocsf".into(),
        hooks: vec![],
        mode: PluginMode::Audit,
        priority: 50,
        on_error: OnError::Fail,
        config: Some(json!({
            "chain": false,
            "product_name": "AI Identity OCSF Audit",
            "vendor_name": "AI Identity",
        })),
        ..Default::default()
    };
    OcsfAuditEmitter::new(config).expect("valid demo config")
}

/// The request under judgement: an agent invoking the `get_compensation`
/// HR tool on behalf of alice@corp.com.
fn tool_request() -> (MessagePayload, Extensions) {
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

    let ext = Extensions {
        security: Some(Arc::new(sec)),
        ..Default::default()
    };
    (payload, ext)
}

/// Build a finalized DecisionLog the way the executor would: ordered
/// per-plugin steps, a terminal verdict, the invocation span, and the
/// seam's completeness/ordering stamps.
fn finalized(
    steps: Vec<(&str, PluginMode, PluginAction)>,
    verdict: Verdict,
    stream_seq: u64,
    emission_seq: u64,
) -> DecisionLog {
    let mut log = DecisionLog::new();
    for (name, mode, action) in steps {
        log.record(name, mode, action);
    }
    log.set_span(Span {
        trace_id: "4bf92f3577b34da6a3ce929d0e0e4736".into(),
        span_id: format!("00f067aa0ba9{:04}", emission_seq),
        parent_span_id: Some("00f067aa0ba90200".into()),
    });
    log.set_stream(1_755_648_000_000_000_000, "gw-1/boot-7".into(), stream_seq, emission_seq);
    log.finalize(verdict);
    log
}

fn main() {
    let e = sink();
    let (payload, ext) = tool_request();

    // 1. Clean allow: PDP and PII scan both passed.
    let allow = finalized(
        vec![
            ("cedar-pdp", PluginMode::Sequential, PluginAction::Allowed),
            ("pii-scan", PluginMode::Sequential, PluginAction::Allowed),
        ],
        Verdict::Allow,
        41,
        41,
    );

    // 2. Allow after modification: the redactor rewrote the payload.
    let modified = finalized(
        vec![
            ("cedar-pdp", PluginMode::Sequential, PluginAction::Allowed),
            ("pii-redactor", PluginMode::Transform, PluginAction::ModifiedPayload),
        ],
        Verdict::Allow,
        42,
        42,
    );

    // 3. Deny: the PDP blocked the call. The violation the executor
    //    stamped rides into status_code / status_detail.
    let mut violation = PluginViolation::new(
        "policy_denied",
        "cedar-pdp: subject lacks permission read_compensation on hr/get_compensation",
    );
    violation.plugin_name = Some("cedar-pdp".into());
    let denied = finalized(
        vec![("cedar-pdp", PluginMode::Sequential, PluginAction::Denied)],
        Verdict::Deny(violation),
        43,
        43,
    );

    // 4. The subtle record: a Transform-phase plugin signalled deny and
    //    was suppressed by role (deny_ignored, never re-coded as allow),
    //    and a concurrent branch was cancelled (aborted, distinct from
    //    error). Terminal verdict: Allow. "Every suppressed transform
    //    deny" is one SIEM query on these step actions.
    let suppressed = finalized(
        vec![
            ("cedar-pdp", PluginMode::Sequential, PluginAction::Allowed),
            ("injection-guard", PluginMode::Transform, PluginAction::DenyIgnored),
            ("secondary-scan", PluginMode::Transform, PluginAction::Aborted),
        ],
        Verdict::Allow,
        44,
        44,
    );

    let cases = [
        ("1 — Allow (clean)", &allow, "2026-08-21T03:20:00.000Z"),
        ("2 — Allow after modification", &modified, "2026-08-21T03:20:01.000Z"),
        ("3 — Deny (policy violation)", &denied, "2026-08-21T03:20:02.000Z"),
        ("4 — Suppressed deny + aborted branch", &suppressed, "2026-08-21T03:20:03.000Z"),
    ];

    for (title, log, ts) in cases {
        let ev = e.build_decision(Some(&payload), &ext, log, ts);
        println!("// ===== Decision {title} =====");
        println!("{}", serde_json::to_string_pretty(&ev).unwrap());
        println!();
    }
}
