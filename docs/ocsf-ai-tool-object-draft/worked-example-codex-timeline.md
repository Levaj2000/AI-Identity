# Worked example — Dave's Codex timeline, event by event (ocsf-schema#1729)

> Written as the worked example for
> [ocsf/ocsf-schema#1729](https://github.com/ocsf/ocsf-schema/pull/1729),
> adopting the Codex/Jira walkthrough Dave McCormack proposed in the WG
> discussion (2026-08-19). Field shapes verified against the PR branch @
> `cab6dc0` (`ai_tool`, `ai_operation` profile) and `main` @ `40a1511`
> (`api_activity` 6003, `process_activity` 1007, `script_activity` 1009,
> `ai_agent`, `script`, `api`, `metadata`), schema version `1.10.0-dev`.
> This file doubles as the ready-to-post PR comment.

---

The scenario is Dave's, verbatim: a user asks Codex *"what is the current
status of Jira ticket PROJ-1234?"*; the agent reads the Jira ticket via the
Atlassian MCP server, the linked PR via the GitHub MCP server, the CI status
via the Jenkins MCP server, then runs local `git` to check the branch, and
reports back. Five discrete events, exactly as the timeline model says —
`ai_tool` changes none of the classes, none of the activity ids, and none of
the event boundaries. It only makes each entry say **which capability was
involved**.

## The correlation spine (three grains)

| Grain | Field | Value in this example | Answers |
|---|---|---|---|
| Session | `ai_agent.instance_uid` | `sess-9c41d2` | "everything this agent instance did" (sub-agents report the same value) |
| Prompt / turn | `metadata.correlation_uid` | `turn-0001` | "which prompt caused this fan-out" (a session spans many prompts) |
| Invocation | `ai_tool.transaction_uid` | `rpc-101` … | pairs a call with its result — including across requestor- and responder-side records |

Shared on every event below (elided from the JSON after the first use):

```json
"ai_agent": { "name": "Codex", "uid": "codex", "type_id": 1, "instance_uid": "sess-9c41d2" },
"actor": { "app_name": "Codex", "user": { "name": "jdoe", "uid": "jdoe@example.com" } }
```

## Step 1 — the user prompt → `script_activity` (1009)

Per the timeline model, the prompt submission is its own discrete event.
(If the WG later prefers a dedicated `user_prompt_activity` class, only this
event changes — the four below are untouched.)

```json
{
  "class_uid": 1009, "category_uid": 1, "activity_id": 1, "activity_name": "Execute",
  "type_uid": 100901, "severity_id": 1, "time": 1787148120000,
  "metadata": { "version": "1.10.0-dev", "uid": "evt-0001", "correlation_uid": "turn-0001" },
  "device": { "hostname": "dev-laptop-042" },
  "script": {
    "name": "user prompt",
    "type_id": 99, "type": "Natural Language",
    "script_content": "what is the current status of Jira ticket PROJ-1234?"
  },
  "ai_agent": { "name": "Codex", "uid": "codex", "type_id": 1, "instance_uid": "sess-9c41d2" },
  "actor": { "app_name": "Codex", "user": { "name": "jdoe", "uid": "jdoe@example.com" } }
}
```

## Step 2 — Jira ticket read via Atlassian MCP → `api_activity` (6003)

```json
{
  "class_uid": 6003, "category_uid": 6, "activity_id": 2, "activity_name": "Read",
  "type_uid": 600302, "severity_id": 1, "status_id": 1, "time": 1787148122000,
  "metadata": { "version": "1.10.0-dev", "uid": "evt-0002", "correlation_uid": "turn-0001" },
  "api": { "operation": "tools/call", "request": { "uid": "rpc-101" } },
  "src_endpoint": { "hostname": "dev-laptop-042" },
  "dst_endpoint": { "hostname": "mcp.atlassian.example.com", "port": 443 },
  "ai_tool": {
    "name": "jira_get_issue",
    "uid": "atlassian-mcp/jira_get_issue",
    "type_id": 1, "type": "Tool",
    "source_id": 1, "source": "MCP",
    "service": { "uid": "atlassian-mcp", "name": "Atlassian MCP Server", "version": "1.4.2" },
    "transport_id": 2, "transport": "Streamable HTTP",
    "is_readonly": true,
    "transaction_uid": "rpc-101",
    "input_schema_fingerprint": {
      "algorithm_id": 3, "algorithm": "SHA-256",
      "serialization_id": 2, "serialization": "JCS",
      "value": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
    }
  },
  "resources": [ { "name": "PROJ-1234", "type": "Jira issue" } ]
}
```

`activity_id: 2` (Read) is derived from the declared `readOnlyHint`
consistent with observed behavior, per the profile guidance; the hint itself
is recorded at `ai_tool.is_readonly` so a consumer can audit the derivation.

## Step 4 — PR metadata read via GitHub MCP → `api_activity` (6003)

```json
{
  "class_uid": 6003, "category_uid": 6, "activity_id": 2, "activity_name": "Read",
  "type_uid": 600302, "severity_id": 1, "status_id": 1, "time": 1787148129000,
  "metadata": { "version": "1.10.0-dev", "uid": "evt-0003", "correlation_uid": "turn-0001" },
  "api": { "operation": "tools/call", "request": { "uid": "rpc-102" } },
  "src_endpoint": { "hostname": "dev-laptop-042" },
  "dst_endpoint": { "hostname": "api.githubcopilot.example.com", "port": 443 },
  "ai_tool": {
    "name": "get_pull_request",
    "uid": "github-mcp/get_pull_request",
    "type_id": 1, "type": "Tool",
    "source_id": 1, "source": "MCP",
    "service": { "uid": "github-mcp", "name": "GitHub MCP Server", "version": "0.9.1" },
    "transport_id": 2, "transport": "Streamable HTTP",
    "is_readonly": true,
    "transaction_uid": "rpc-102"
  },
  "resources": [ { "name": "acme/checkout-service#812", "type": "GitHub pull request" } ]
}
```

## Step 6 — CI status read via Jenkins MCP → `api_activity` (6003)

```json
{
  "class_uid": 6003, "category_uid": 6, "activity_id": 2, "activity_name": "Read",
  "type_uid": 600302, "severity_id": 1, "status_id": 1, "time": 1787148135000,
  "metadata": { "version": "1.10.0-dev", "uid": "evt-0004", "correlation_uid": "turn-0001" },
  "api": { "operation": "tools/call", "request": { "uid": "rpc-103" } },
  "src_endpoint": { "hostname": "dev-laptop-042" },
  "dst_endpoint": { "hostname": "jenkins-mcp.internal.example.com", "port": 443 },
  "ai_tool": {
    "name": "get_build_status",
    "uid": "jenkins-mcp/get_build_status",
    "type_id": 1, "type": "Tool",
    "source_id": 1, "source": "MCP",
    "service": { "uid": "jenkins-mcp", "name": "Jenkins MCP Server", "version": "2.1.0" },
    "transport_id": 2, "transport": "Streamable HTTP",
    "is_readonly": true,
    "transaction_uid": "rpc-103"
  },
  "resources": [ { "name": "checkout-service/pipeline/812", "type": "Jenkins pipeline" } ]
}
```

Without `ai_tool`, this event and the two above are structurally identical
`api_activity` records — three "some API call happened" events. With it,
each one says which primitive was invoked, which server served it, over
which transport, and what it declared about itself.

## Step 8 — local `git` via the agent's shell tool → `process_activity` (1007)

The launched process is the event's subject (`process`), exactly as an
endpoint product would record it. `ai_tool` adds the *agent-layer cause*:
this launch was the agent's shell tool acting, not an unrelated process.
One correction to my Slack shorthand (`{name: "git"}`): the capability is
the agent's **shell tool**; `git` is the command it ran, and that belongs on
`process.cmd_line` — the object model keeps the two apart, which is the
point.

```json
{
  "class_uid": 1007, "category_uid": 1, "activity_id": 1, "activity_name": "Launch",
  "type_uid": 100701, "severity_id": 1, "time": 1787148141000,
  "metadata": { "version": "1.10.0-dev", "uid": "evt-0005", "correlation_uid": "turn-0001" },
  "device": { "hostname": "dev-laptop-042" },
  "process": {
    "pid": 48213,
    "cmd_line": "git status --porcelain=v2 --branch",
    "file": { "name": "git", "path": "/usr/bin/git" }
  },
  "ai_tool": {
    "name": "shell",
    "uid": "codex/shell",
    "type_id": 1, "type": "Tool",
    "source_id": 2, "source": "Function",
    "transaction_uid": "call-l7"
  }
}
```

No MCP anywhere in this event — `source_id: 2 (Function)` and the absent
`service`/`transport` say so honestly. This is why the object is
protocol-neutral rather than MCP-specific: it is the one field that links an
endpoint-native event back to the agent's tool-call layer.

## The requestor/responder join

The five events above are the **requestor-side** view. If the Atlassian MCP
server (or a collector on its side) also emits OCSF, its record of step 2 is
a second `api_activity` from the opposite vantage — different `actor`,
different endpoints, its own disposition — carrying the same two join keys:

```json
"ai_tool": {
  "name": "jira_get_issue",
  "service": { "uid": "atlassian-mcp" },
  "transaction_uid": "rpc-101"
}
```

`(ai_tool.service.uid, ai_tool.transaction_uid)` stitches the two views of
one invocation into one narrative — and a *disagreement* between them
(requestor recorded a call the responder never served, or vice versa) is
itself a detection signal. Today that join has no schema home on either
side.

## What becomes queryable

From these five events, with nothing but the fields above:

- *"Every call this agent made to the Jenkins MCP server"* — `ai_tool.service.uid = "jenkins-mcp"`.
- *"Did anything write-capable run in this session?"* — `ai_agent.instance_uid = "sess-9c41d2" AND ai_tool.is_readonly != true`.
- *"Which prompt caused the local process launch?"* — `metadata.correlation_uid` joins event 5 back to event 1.
- *"Did this tool's contract drift since approval?"* — group by `ai_tool.input_schema_fingerprint.value`.

None of these are answerable from the same five events without `ai_tool` —
the data is either absent (serving server, hints, contracts) or buried in
free-text operation names.
