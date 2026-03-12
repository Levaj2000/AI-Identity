/** API response types — mirrors Pydantic schemas from common/schemas/ */

export interface Agent {
  id: string
  user_id: string
  name: string
  description: string | null
  status: 'active' | 'suspended' | 'revoked'
  capabilities: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AgentListResponse {
  items: Agent[]
  total: number
  limit: number
  offset: number
}

export interface HealthResponse {
  status: string
  version: string
  service: string
}

export interface DashboardStats {
  totalAgents: number
  activeAgents: number
  suspendedAgents: number
  revokedAgents: number
}

export interface ApiError {
  status: number
  code: string
  message: string
}
