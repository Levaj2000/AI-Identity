/**
 * TypeScript interfaces mirroring backend Pydantic schemas.
 *
 * Generated from OpenAPI spec at /openapi.json — keep in sync
 * when backend schemas change.
 */

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
}

export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface ValidationErrorResponse {
  detail: ValidationErrorItem[]
}
