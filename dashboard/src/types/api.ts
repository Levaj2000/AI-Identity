/**
 * TypeScript interfaces mirroring backend Pydantic schemas.
 *
 * Generated from OpenAPI spec at /openapi.json — keep in sync
 * when backend schemas change.
 */

// ─── Capabilities ───────────────────────────────────────────────

export interface CapabilityDefinition {
  id: string
  name: string
  description: string
  endpoints: string[]
  methods: string[]
}

// ─── Agent ───────────────────────────────────────────────────────

export type AgentStatus = 'active' | 'suspended' | 'revoked'

export interface Agent {
  id: string
  user_id: string
  name: string
  description: string | null
  status: AgentStatus
  capabilities: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  description?: string | null
  capabilities?: string[]
  metadata?: Record<string, unknown>
}

export interface AgentUpdate {
  name?: string | null
  description?: string | null
  capabilities?: string[] | null
  metadata?: Record<string, unknown> | null
  status?: 'active' | 'suspended' | null
}

export interface AgentCreateResponse {
  agent: Agent
  /** Plaintext API key (aid_sk_…) — shown only once at creation time */
  api_key: string
}

export interface AgentListResponse {
  items: Agent[]
  total: number
  limit: number
  offset: number
}

export interface AgentListParams {
  status?: AgentStatus
  capability?: string
  limit?: number
  offset?: number
}

// ─── Agent Key ───────────────────────────────────────────────────

export type KeyStatus = 'active' | 'rotated' | 'revoked'
export type KeyType = 'runtime' | 'admin'

export interface AgentKey {
  id: number
  agent_id: string
  key_prefix: string
  key_type: KeyType
  status: KeyStatus
  expires_at: string | null
  created_at: string
}

export interface AgentKeyCreateResponse {
  key: AgentKey
  /** Plaintext API key (aid_sk_…) — shown only once */
  api_key: string
}

export interface AgentKeyListResponse {
  items: AgentKey[]
  total: number
}

export interface AgentKeyRotateResponse {
  new_key: AgentKey
  /** Plaintext API key for the new key — shown only once */
  api_key: string
  /** The old key, now with status=rotated and a 24hr expiry */
  rotated_key: AgentKey
}

// ─── Health ──────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version: string
  service: string
}

// ─── Dashboard (client-side computed) ────────────────────────────

export interface DashboardStats {
  totalAgents: number
  activeAgents: number
  suspendedAgents: number
  revokedAgents: number
}

// ─── Errors ──────────────────────────────────────────────────────

export interface ApiError {
  status: number
  code: string
  message: string
  /** Raw validation error items — only populated on 422 responses. */
  validationErrors?: ValidationErrorItem[]
}

export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface ValidationErrorResponse {
  detail: ValidationErrorItem[]
}

// ─── Forensics ────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: number
  agent_id: string
  user_id: string | null
  endpoint: string
  method: string
  decision: string
  cost_estimate_usd: number | null
  latency_ms: number | null
  request_metadata: Record<string, unknown>
  entry_hash: string
  prev_hash: string
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

export interface TopEndpoint {
  endpoint: string
  count: number
}

export interface AuditStatsResponse {
  total_events: number
  allowed_count: number
  denied_count: number
  error_count: number
  total_cost_usd: number
  avg_latency_ms: number | null
  top_endpoints: TopEndpoint[]
}

export interface ChainVerifyResponse {
  valid: boolean
  total_entries: number
  entries_verified: number
  first_broken_id: number | null
  message: string
}

export interface PolicySnapshot {
  id: number
  agent_id: string
  rules: Record<string, unknown>
  version: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuditReconstructResponse {
  agent_id: string
  agent_name: string | null
  start_date: string
  end_date: string
  events: AuditLogEntry[]
  chain_verification: ChainVerifyResponse
  active_policy: PolicySnapshot | null
  stats: AuditStatsResponse
}

export interface ForensicsReportResponse {
  report_id: string
  generated_at: string
  agent: Record<string, unknown>
  time_window: { start: string; end: string }
  events: AuditLogEntry[]
  chain_verification: ChainVerifyResponse
  active_policy: PolicySnapshot | null
  stats: AuditStatsResponse
}

export interface ForensicsFilterParams {
  agent_id?: string
  start_date?: string
  end_date?: string
  decision?: string
  endpoint?: string
  action_type?: string
  model?: string
  cost_min?: number
  cost_max?: number
  limit?: number
  offset?: number
}

// ─── Organizations ────────────────────────────────────────────────

export interface Organization {
  id: string
  name: string
  owner_id: string
  tier: string
  member_count: number
  agent_count: number
  created_at: string
}

export interface OrgMember {
  user_id: string
  email: string
  role: 'owner' | 'admin' | 'member'
  joined_at: string
}

export interface AgentAssignment {
  user_id: string
  email: string
  role: 'owner' | 'operator' | 'viewer'
  created_at: string
}
