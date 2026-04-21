export interface DocSection {
  id: string;
  title: string;
  content: DocBlock[];
}

export type DocBlock =
  | { type: "text"; body: string }
  | { type: "code"; language: string; title?: string; body: string }
  | { type: "steps"; items: { title: string; description: string; code?: string }[] }
  | { type: "cards"; items: { title: string; description: string; icon?: string }[] }
  | { type: "links"; items: { label: string; href: string; description: string }[] };

export const docSections: DocSection[] = [
  {
    id: "quickstart",
    title: "Quickstart",
    content: [
      {
        type: "text",
        body: "Get up and running with AI Identity in under 5 minutes. Follow these four steps to register your first agent, obtain an API key, route traffic through the gateway, and explore forensic logs.",
      },
      {
        type: "steps",
        items: [
          {
            title: "1. Create an Agent",
            description:
              "Register a new AI agent with a unique identity. Every agent gets a cryptographic fingerprint that follows it across every request.",
            code: `curl -X POST https://gateway.ai-identity.co/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "support-bot",
    "description": "Customer support assistant",
    "allowed_models": ["gpt-4o", "claude-sonnet-4-20250514", "gemini-2.5-pro"]
  }'`,
          },
          {
            title: "2. Get an API Key",
            description:
              "Generate a scoped API key for your agent. Keys can be restricted by model, rate limit, and expiration date.",
            code: `curl -X POST https://gateway.ai-identity.co/v1/agents/ag_abc123/keys \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "production-key",
    "scopes": ["chat:completions", "embeddings"],
    "rate_limit": 100,
    "expires_in_days": 90
  }'`,
          },
          {
            title: "3. Point Your Gateway",
            description:
              "Replace your LLM provider base URL with the AI Identity gateway. All requests are transparently proxied with identity headers injected.",
            code: `# Instead of calling your LLM provider directly:
# POST https://api.openai.com/v1/chat/completions
# POST https://api.anthropic.com/v1/messages

# Point ALL providers to the AI Identity gateway:
curl -X POST https://gateway.ai-identity.co/v1/chat/completions \\
  -H "Authorization: Bearer aid_sk_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [
      {"role": "user", "content": "Hello, world!"}
    ]
  }'
# Works with gpt-4o, claude-sonnet-4-20250514, gemini-2.5-pro, etc.`,
          },
          {
            title: "4. Explore Forensics",
            description:
              "Every request through the gateway is logged with a tamper-proof audit trail. Query the forensics API to see what your agents have been doing.",
            code: `curl https://gateway.ai-identity.co/v1/agents/ag_abc123/logs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -G \\
  -d "limit=10" \\
  -d "since=2025-01-01T00:00:00Z"`,
          },
        ],
      },
    ],
  },
  {
    id: "core-concepts",
    title: "Core Concepts",
    content: [
      {
        type: "text",
        body: "AI Identity is built around four pillars that together provide a comprehensive governance layer for autonomous AI agents.",
      },
      {
        type: "cards",
        items: [
          {
            title: "Identity",
            icon: "fingerprint",
            description:
              "Every AI agent gets a unique, scoped aid_sk_ API key. Keys are SHA-256 hashed at rest, rotated with zero downtime, and revoked per-agent. Shadow Agent Detection automatically surfaces unregistered agents hitting the gateway so you can Register, Block, or Dismiss them.",
          },
          {
            title: "Policy",
            icon: "shield",
            description:
              "ABAC on agent metadata lets you write fine-grained policies (model allowlists, tool allowlists, rate limits, spend caps, time-of-day). The policy dry-run endpoint lets you test policy changes against real traffic before rollout. Capability templates auto-generate safe defaults.",
          },
          {
            title: "Compliance",
            icon: "check",
            description:
              "Automated control mapping for EU AI Act (Articles 9, 12, 13, 14), SOC 2 (CC6.x, CC7), NIST AI RMF (MEASURE), ISO 27001 (A.12 / A.13), and GDPR (Article 30). Export evidence bundles with chain-of-custody certificates and per-framework profiles.",
          },
          {
            title: "Forensics",
            icon: "search",
            description:
              "HMAC-SHA256 hash-chained audit log with org scoping + correlation IDs across gateway, API, and control plane. Every session is closed with a DSSE + ECDSA P-256 signed attestation. Verify any export offline — no database, no network, no trust in our servers required.",
          },
        ],
      },
    ],
  },
  {
    id: "gateway",
    title: "Gateway Architecture",
    content: [
      {
        type: "text",
        body: "The AI Identity Gateway sits between your application and your LLM providers. It acts as a transparent proxy that injects identity headers, enforces policies, and logs every interaction \u2014 all without changing your existing code.",
      },
      {
        type: "code",
        language: "text",
        title: "Request flow",
        body: `Your App  \u2192  AI Identity Gateway  \u2192  LLM Provider (OpenAI, Anthropic, Gemini, Cohere, Mistral, etc.)
                     \u2502
                     \u251c\u2500 Validate agent identity
                     \u251c\u2500 Check policy (rate limit, model access, budget)
                     \u251c\u2500 Inject audit headers (X-Agent-ID, X-Request-ID)
                     \u251c\u2500 Log request metadata
                     \u2514\u2500 Forward to upstream provider`,
      },
      {
        type: "text",
        body: "The gateway works with any LLM provider — OpenAI, Anthropic, Google Gemini, Cohere, Mistral, or any custom REST API. Simply change your base URL and use your AI Identity agent key instead of a provider key. The gateway routes to the correct upstream provider based on the model specified in the request.",
      },
      {
        type: "code",
        language: "python",
        title: "Python — OpenAI models via the gateway",
        body: `from openai import OpenAI

# Point the OpenAI client at the AI Identity gateway
client = OpenAI(
    base_url="https://gateway.ai-identity.co/v1",
    api_key="aid_sk_your_agent_key",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize today's news"}],
)
print(response.choices[0].message.content)`,
      },
      {
        type: "code",
        language: "python",
        title: "Python — Anthropic models via the gateway",
        body: `from openai import OpenAI

# Same gateway, different model — Anthropic Claude
client = OpenAI(
    base_url="https://gateway.ai-identity.co/v1",
    api_key="aid_sk_your_agent_key",
)

response = client.chat.completions.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Explain quantum computing"}],
)
print(response.choices[0].message.content)`,
      },
      {
        type: "code",
        language: "typescript",
        title: "TypeScript — any model via the gateway",
        body: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://gateway.ai-identity.co/v1",
  apiKey: "aid_sk_your_agent_key",
});

// Works with any supported model — OpenAI, Anthropic, Gemini, etc.
const response = await client.chat.completions.create({
  model: "gemini-2.5-pro",  // or "gpt-4o", "claude-sonnet-4-20250514", etc.
  messages: [{ role: "user", content: "Summarize today's news" }],
});
console.log(response.choices[0].message.content);`,
      },
    ],
  },
  {
    id: "integrations",
    title: "Integrations",
    content: [
      {
        type: "text",
        body: "AI Identity works with all major agent frameworks and LLM providers — OpenAI, Anthropic, Google Gemini, Cohere, Mistral, and more. Because the gateway uses the OpenAI-compatible API format, integration usually requires changing just one line — the base URL.",
      },
      {
        type: "code",
        language: "python",
        title: "LangChain",
        body: `from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o",
    base_url="https://gateway.ai-identity.co/v1",
    api_key="aid_sk_your_agent_key",
)

response = llm.invoke("What is AI Identity?")
print(response.content)`,
      },
      {
        type: "code",
        language: "python",
        title: "CrewAI",
        body: `import os
os.environ["OPENAI_API_BASE"] = "https://gateway.ai-identity.co/v1"
os.environ["OPENAI_API_KEY"] = "aid_sk_your_agent_key"

from crewai import Agent, Task, Crew

researcher = Agent(
    role="Researcher",
    goal="Find the latest AI governance news",
    backstory="You are an expert AI policy analyst.",
    llm="gpt-4o",
)

task = Task(
    description="Summarize recent developments in AI regulation",
    expected_output="A concise briefing document",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
print(result)`,
      },
      {
        type: "code",
        language: "python",
        title: "AutoGen",
        body: `from autogen import AssistantAgent, UserProxyAgent

config_list = [{
    "model": "gpt-4o",
    "base_url": "https://gateway.ai-identity.co/v1",
    "api_key": "aid_sk_your_agent_key",
}]

assistant = AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
)

user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    code_execution_config=False,
)

user_proxy.initiate_chat(
    assistant, message="Explain how AI identity governance works."
)`,
      },
      {
        type: "code",
        language: "bash",
        title: "Direct cURL",
        body: `# List your agents
curl https://gateway.ai-identity.co/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY"

# Create a chat completion through the gateway (any provider)
curl -X POST https://gateway.ai-identity.co/v1/chat/completions \\
  -H "Authorization: Bearer aid_sk_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Check agent usage and forensic logs
curl https://gateway.ai-identity.co/v1/agents/ag_abc123/usage \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      },
    ],
  },
  {
    id: "authentication",
    title: "Authentication",
    content: [
      {
        type: "text",
        body: "AI Identity uses API key authentication. There are two types of keys: organization keys (for managing agents and viewing logs) and agent keys (for making LLM requests through the gateway).",
      },
      {
        type: "cards",
        items: [
          {
            title: "Organization Keys",
            icon: "key",
            description:
              "Prefixed with aid_org_. Used for management operations: creating agents, generating agent keys, viewing logs, and configuring policies. Keep these secure and never expose them in client-side code.",
          },
          {
            title: "Agent Keys",
            icon: "bot",
            description:
              "Prefixed with aid_sk_. Scoped to a single agent. Used for making LLM requests through the gateway. Each key inherits the policies attached to its agent. Rotate these regularly.",
          },
        ],
      },
      {
        type: "code",
        language: "bash",
        title: "Authentication header format",
        body: `# Organization-level operations
curl https://gateway.ai-identity.co/v1/agents \\
  -H "Authorization: Bearer aid_org_your_org_key"

# Agent-level LLM requests
curl -X POST https://gateway.ai-identity.co/v1/chat/completions \\
  -H "Authorization: Bearer aid_sk_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "claude-sonnet-4-20250514", "messages": [{"role": "user", "content": "Hi"}]}'`,
      },
    ],
  },
  {
    id: "policies",
    title: "Policies (ABAC + dry-run)",
    content: [
      {
        type: "text",
        body: "Policies use ABAC (attribute-based access control) over agent metadata. Conditions can reference any attribute on the agent, the request, or the caller. Every policy change can be tested against live traffic using the dry-run endpoint before you enforce it.",
      },
      {
        type: "code",
        language: "bash",
        title: "Create an ABAC policy",
        body: `curl -X POST https://api.ai-identity.co/v1/policies \\
  -H "Authorization: Bearer aid_org_your_org_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "support-agents-read-only-crm",
    "effect": "allow",
    "conditions": {
      "agent.team": "support",
      "agent.environment": "prod",
      "request.tool": { "in": ["crm.read", "kb.search"] },
      "request.hour_utc": { "between": [13, 23] }
    },
    "limits": { "rpm": 60, "monthly_usd_cap": 500 }
  }'`,
      },
      {
        type: "code",
        language: "bash",
        title: "Dry-run a policy change against real traffic",
        body: `# See how a proposed policy would have ruled on the last 24h of requests
curl -X POST https://api.ai-identity.co/v1/policies/dry-run \\
  -H "Authorization: Bearer aid_org_your_org_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "policy": { /* same body as POST /v1/policies */ },
    "window": "24h"
  }'

# Returns per-request decisions: allow / deny / would-change
# so you can confirm the policy is safe before enforcing it.`,
      },
      {
        type: "text",
        body: "Capability templates auto-generate safe default policies for common agent roles (support, coding assistant, research, back-office). Tier-based quota enforcement applies organization-wide caps — policies compose with quotas rather than replacing them.",
      },
    ],
  },
  {
    id: "hitl-approvals",
    title: "Human-in-the-Loop Approvals",
    content: [
      {
        type: "text",
        body: "Enterprise-tier agents can be configured to pause and request human approval before executing high-risk actions — for example, sending customer emails, issuing refunds, or writing to production databases. Approvals go to a reviewer queue in the dashboard and can be accepted, rejected, or escalated.",
      },
      {
        type: "code",
        language: "bash",
        title: "Require HITL approval for a tool",
        body: `curl -X POST https://api.ai-identity.co/v1/policies \\
  -H "Authorization: Bearer aid_org_your_org_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "refunds-require-approval",
    "effect": "require_approval",
    "conditions": { "request.tool": "billing.refund" },
    "approval": {
      "reviewer_team": "finance-ops",
      "timeout_seconds": 900,
      "on_timeout": "deny"
    }
  }'`,
      },
      {
        type: "text",
        body: "Pending approvals appear in the dashboard under Approvals. The agent receives a 202 Accepted response while waiting, polls for the decision, and either proceeds or fails closed on timeout. All approval decisions are written into the hash-chained audit log with reviewer identity and reasoning.",
      },
    ],
  },
  {
    id: "shadow-agents",
    title: "Shadow Agent Detection",
    content: [
      {
        type: "text",
        body: "Shadow Agent Detection identifies unregistered or unknown agents that hit the gateway — either because a team spun one up without central oversight, or because a credential is being reused. Each detection drops into the Shadow Agents page with full request metadata and three actions: Register (onboard with scoped policy), Block (deny all future requests), or Dismiss (stop alerting).",
      },
      {
        type: "cards",
        items: [
          {
            title: "Deep-link to Forensics",
            icon: "search",
            description:
              "Every shadow-agent entry deep-links to the Forensics view with the agent_id pre-filled and a ±1 hour window around the detection — pivot from alert to evidence in one click.",
          },
          {
            title: "Auto-policy on Register",
            icon: "shield",
            description:
              "Registering a shadow agent seeds a default policy from the closest capability template, so the agent becomes governed immediately rather than sitting in an unscoped state.",
          },
        ],
      },
    ],
  },
  {
    id: "forensic-attestations",
    title: "Forensic Attestations",
    content: [
      {
        type: "text",
        body: "The audit log is HMAC-SHA256 hash-chained — every entry references the previous entry's hash, so any tampering breaks the chain. When a session closes, the gateway produces a DSSE-wrapped attestation signed with an ECDSA P-256 key held in Cloud KMS. Public keys are published at a stable JWKS endpoint, so auditors can verify signatures without trusting our servers.",
      },
      {
        type: "code",
        language: "bash",
        title: "Fetch attestations and public JWKS",
        body: `# 1. Get a session's signed attestation envelope
curl https://api.ai-identity.co/v1/attestations/sess_8f2a4c71b9 \\
  -H "Authorization: Bearer aid_org_your_org_key" \\
  -o attestation.json

# 2. Fetch the public JWKS — no auth required
curl https://api.ai-identity.co/.well-known/jwks.json -o jwks.json`,
      },
      {
        type: "code",
        language: "bash",
        title: "Verify offline with the AI Identity CLI",
        body: `# The verification CLI is a single Python file, stdlib-only for chain checks.
# Install:
pip install cryptography   # only needed for attestation signature verification
cp cli/ai_identity_verify.py /usr/local/bin/ai_identity_verify
chmod +x /usr/local/bin/ai_identity_verify

# Verify a forensics export's HMAC chain of custody:
export AI_IDENTITY_HMAC_KEY='your-hmac-secret'
ai_identity_verify chain audit_export.json --verbose

# Verify a forensics report signature:
ai_identity_verify report forensics_report.json

# Verify a signed session attestation envelope (no server required):
ai_identity_verify attestation attestation.json --jwks jwks.json`,
      },
      {
        type: "text",
        body: "All three verifications are fully offline — the CLI reads your export file + public JWKS and returns a deterministic result. You do not need to trust AI Identity's servers, our code, or our availability. This is the same verification flow auditors follow during SOC 2 and EU AI Act reviews.",
      },
    ],
  },
  {
    id: "observability",
    title: "Observability & SIEM",
    content: [
      {
        type: "text",
        body: "AI Identity emits Prometheus metrics for the gateway, API, and audit log pipeline. Every request carries a correlation ID that threads through gateway → policy → upstream → audit → attestation so you can reconstruct cross-service activity from a single ID. Audit events can be forwarded to your SIEM as signed webhooks using the outbox pattern.",
      },
      {
        type: "cards",
        items: [
          {
            title: "Prometheus /metrics",
            icon: "search",
            description:
              "Scrape gateway RPS, policy allow/deny rates, audit-write failures (paged, never deduplicated), outbox lag, and attestation signing latency. Dashboards live in Grafana on top of Google Managed Prometheus — customer SREs can self-serve alerts without a UI dependency on us.",
          },
          {
            title: "Signed SIEM webhooks",
            icon: "shield",
            description:
              "Audit log forwarding uses the outbox pattern — every entry is written once to Postgres and reliably pushed to your SIEM as a signed webhook. Verifies with the same public JWKS used for session attestations. Splunk and Datadog connectors on top of this primitive are on the near-term roadmap.",
          },
        ],
      },
      {
        type: "code",
        language: "bash",
        title: "Configure a SIEM webhook sink",
        body: `curl -X POST https://api.ai-identity.co/v1/audit/sinks \\
  -H "Authorization: Bearer aid_org_your_org_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "kind": "webhook",
    "url": "https://siem.internal.example.com/ingest/ai-identity",
    "events": ["policy.deny", "approval.decision", "shadow_agent.detected", "session.close"],
    "signing": { "jwks": "https://api.ai-identity.co/.well-known/jwks.json" }
  }'`,
      },
    ],
  },
  {
    id: "compliance-export",
    title: "Compliance Export",
    content: [
      {
        type: "text",
        body: "The compliance export API produces evidence bundles mapped to specific control frameworks. Each profile returns the subset of audit records, attestations, and policy decisions relevant to the framework, plus a chain-of-custody certificate the bundle can be verified against offline.",
      },
      {
        type: "code",
        language: "bash",
        title: "Export an EU AI Act evidence bundle",
        body: `curl -X POST https://api.ai-identity.co/v1/compliance/exports \\
  -H "Authorization: Bearer aid_org_your_org_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "profile": "eu_ai_act",
    "window": { "start": "2026-01-01", "end": "2026-03-31" }
  }'

# Response contains a download URL for the signed bundle.
# Profiles live today (stub endpoints): soc2, eu_ai_act, nist_ai_rmf
# Additional profiles on the near-term roadmap: iso_27001, hipaa`,
      },
      {
        type: "text",
        body: "The mapping is intentionally transparent — the response lists which controls the bundle covers, which are partial, and which are explicitly out of scope. You can see exactly what AI Identity attests to versus what your auditor still needs to collect separately.",
      },
    ],
  },
  {
    id: "infrastructure",
    title: "Infrastructure & Security",
    content: [
      {
        type: "text",
        body: "AI Identity runs on Google Kubernetes Engine (Autopilot) with defense-in-depth hardening. The public-facing control plane is the only surface auditors need to trust — the cluster, the database, and the signing path are all locked down.",
      },
      {
        type: "cards",
        items: [
          {
            title: "Cluster hardening",
            icon: "shield",
            description:
              "Binary Authorization in ENFORCE mode — only attested, digest-pinned images run. Pod Security Admission at restricted. Non-root containers, read-only root filesystems, dropped Linux capabilities. NetworkPolicies are default-deny with explicit allow-lists (including NodeLocal DNSCache egress).",
          },
          {
            title: "Ingress protection",
            icon: "shield",
            description:
              "Cloud Armor WAF in ENFORCE with adaptive DDoS protection and per-IP throttling. HTTPS redirect everywhere. The GKE control plane is reached only through Connect Gateway — Master Authorized Networks are on, there is no public kubectl endpoint.",
          },
          {
            title: "Secrets & credentials",
            icon: "key",
            description:
              "All runtime secrets mounted via Google Secret Manager + CSI driver — no secrets in manifests. Upstream LLM credentials encrypted with Fernet at rest. Signing keys held in Cloud KMS HSM and never leave the HSM boundary.",
          },
          {
            title: "Database security",
            icon: "fingerprint",
            description:
              "PostgreSQL with Row-Level Security in FORCE mode — application-layer query scoping layered on top of database-layer RLS so a compromised service cannot read another org's data. Connections use sslmode=verify-full. Migrations run before rollout, never during.",
          },
        ],
      },
      {
        type: "text",
        body: "Defense-in-depth maps directly to CIS Kubernetes Benchmark controls, SOC 2 CC6.x (logical access) and CC7 (system monitoring), and ISO 27001 A.12 (operations security) and A.13 (communications security). The 48-hour shipping report covering the most recent hardening push is available on request.",
      },
    ],
  },
  {
    id: "api-reference",
    title: "API Reference",
    content: [
      {
        type: "text",
        body: "Full interactive API documentation is available in two formats. Both are auto-generated from the OpenAPI spec and stay in sync with the latest deployed version.",
      },
      {
        type: "links",
        items: [
          {
            label: "ReDoc",
            href: "https://api.ai-identity.co/redoc",
            description:
              "Clean, readable API reference with request/response schemas, example payloads, and authentication details. Best for reading and understanding the API.",
          },
          {
            label: "Swagger UI",
            href: "https://api.ai-identity.co/docs",
            description:
              "Interactive API explorer where you can try endpoints directly from the browser. Best for testing and debugging.",
          },
        ],
      },
      {
        type: "text",
        body: "The API follows RESTful conventions. All endpoints accept and return JSON. Timestamps are ISO 8601 in UTC. Pagination uses cursor-based pagination with limit and after parameters.",
      },
      {
        type: "code",
        language: "bash",
        title: "Common API endpoints",
        body: `# Agents
GET    /v1/agents                         # List all agents
POST   /v1/agents                         # Create a new agent
GET    /v1/agents/:id                     # Get agent details
PATCH  /v1/agents/:id                     # Update an agent
DELETE /v1/agents/:id                     # Delete an agent

# Keys
POST   /v1/agents/:id/keys                # Create an agent key
GET    /v1/agents/:id/keys                # List agent keys
DELETE /v1/agents/:id/keys/:key_id        # Revoke a key

# Policies
GET    /v1/policies                       # List policies
POST   /v1/policies                       # Create a policy
PATCH  /v1/policies/:id                   # Update a policy
POST   /v1/policies/dry-run               # Dry-run against live traffic

# Shadow agents
GET    /v1/shadow-agents                  # List detected shadow agents
POST   /v1/shadow-agents/:id/register     # Register with default policy
POST   /v1/shadow-agents/:id/block        # Block all future requests
POST   /v1/shadow-agents/:id/dismiss      # Dismiss the detection

# Approvals (HITL)
GET    /v1/approvals                      # List pending approvals
POST   /v1/approvals/:id/decide           # Approve / reject with reasoning

# Forensics / Logs
GET    /v1/agents/:id/logs                # Get agent request logs
GET    /v1/agents/:id/usage               # Get usage summary
GET    /v1/attestations/:session_id       # Get signed session attestation
GET    /.well-known/jwks.json             # Public JWKS for verification

# Compliance
POST   /v1/compliance/exports             # Generate an evidence bundle
GET    /v1/compliance/exports/:id         # Download a generated bundle

# Audit sinks (SIEM forwarding)
POST   /v1/audit/sinks                    # Configure a webhook sink
GET    /v1/audit/sinks                    # List configured sinks

# Observability
GET    /metrics                           # Prometheus metrics (internal)

# Gateway (OpenAI-compatible)
POST   /v1/chat/completions               # Proxied chat completion
POST   /v1/embeddings                     # Proxied embeddings`,
      },
    ],
  },
];
