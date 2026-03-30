// ── Agents ──────────────────────────────────────────────────────────────

export interface AgentCreate {
  name: string;
  description?: string;
  capabilities?: unknown[];
  metadata?: Record<string, unknown>;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  capabilities?: unknown[];
  metadata?: Record<string, unknown>;
  status?: "active" | "suspended";
}

export interface Agent {
  id: string;
  user_id: string;
  org_id: string | null;
  name: string;
  description: string | null;
  status: string;
  capabilities: unknown[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentList {
  items: Agent[];
  total: number;
  limit: number;
  offset: number;
}

export interface AgentCreateResponse {
  agent: Agent;
  /** Plaintext API key (aid_sk_…) — shown only once. */
  api_key: string;
}

// ── Keys ────────────────────────────────────────────────────────────────

export interface AgentKey {
  id: number;
  agent_id: string;
  key_prefix: string;
  key_type: string;
  status: string;
  expires_at: string | null;
  created_at: string;
}

export interface AgentKeyCreateResponse {
  key: AgentKey;
  /** Plaintext API key — shown only once. */
  api_key: string;
}

export interface AgentKeyList {
  items: AgentKey[];
  total: number;
}

export interface AgentKeyRotateResponse {
  new_key: AgentKey;
  api_key: string;
  rotated_key: AgentKey;
}

// ── Policies ────────────────────────────────────────────────────────────

export interface PolicyCreate {
  rules: Record<string, unknown>;
}

export interface Policy {
  id: number;
  agent_id: string;
  rules: Record<string, unknown>;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Credentials ─────────────────────────────────────────────────────────

export interface CredentialCreate {
  provider: string;
  api_key: string;
  label?: string;
}

export interface Credential {
  id: number;
  agent_id: string;
  provider: string;
  label: string | null;
  key_prefix: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CredentialCreateResponse {
  credential: Credential;
  message: string;
}

export interface CredentialList {
  items: Credential[];
  total: number;
}

export interface CredentialRotate {
  api_key: string;
}

// ── Audit ───────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: number;
  agent_id: string;
  user_id: string | null;
  endpoint: string;
  method: string;
  decision: string;
  cost_estimate_usd: number | null;
  latency_ms: number | null;
  request_metadata: Record<string, unknown>;
  entry_hash: string;
  prev_hash: string;
  created_at: string;
}

export interface AuditList {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface TopEndpoint {
  endpoint: string;
  count: number;
}

export interface AuditStats {
  total_events: number;
  allowed_count: number;
  denied_count: number;
  error_count: number;
  total_cost_usd: number;
  avg_latency_ms: number | null;
  top_endpoints: TopEndpoint[];
}

export interface AuditChainVerification {
  valid: boolean;
  total_entries: number;
  entries_verified: number;
  first_broken_id: number | null;
  message: string;
}

// ── Params ──────────────────────────────────────────────────────────────

export interface ListParams {
  limit?: number;
  offset?: number;
}

export interface AgentListParams extends ListParams {
  status?: string;
  capability?: string;
}

export interface AuditListParams extends ListParams {
  agent_id?: string;
}
