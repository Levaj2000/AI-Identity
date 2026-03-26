/**
 * Admin API client — platform stats, user management, system health.
 *
 * All endpoints require admin role (403 if not admin).
 */

import { apiFetch, toQueryString } from './client'

// ── Types ───────────────────────────────────────────────────────────

export interface AdminStats {
  total_users: number
  total_agents: number
  total_active_agents: number
  total_requests: number
  users_by_tier: Record<string, number>
  agents_by_status: Record<string, number>
}

export interface AdminUserSummary {
  id: string
  email: string | null
  role: string | null
  tier: string
  requests_this_month: number
  agent_count: number
  has_subscription: boolean
  stripe_customer_id: string | null
  created_at: string | null
}

export interface AdminUserList {
  items: AdminUserSummary[]
  total: number
  limit: number
  offset: number
}

export interface AdminHealth {
  status: string
  db_latency_ms: number
  table_counts: Record<string, number>
}

export interface AdminAgent {
  id: string
  name: string
  status: string
  owner_email: string | null
  key_count: number
  created_at: string | null
}

export interface AdminAgentList {
  items: AdminAgent[]
  total: number
  limit: number
  offset: number
}

// ── API Functions ───────────────────────────────────────────────────

export function getAdminStats(): Promise<AdminStats> {
  return apiFetch<AdminStats>('/api/v1/admin/stats')
}

export function getAdminUsers(params: {
  limit?: number
  offset?: number
  tier?: string
  search?: string
}): Promise<AdminUserList> {
  return apiFetch<AdminUserList>(`/api/v1/admin/users${toQueryString(params)}`)
}

export function updateUserTier(userId: string, tier: string): Promise<AdminUserSummary> {
  return apiFetch<AdminUserSummary>(`/api/v1/admin/users/${userId}/tier`, {
    method: 'PATCH',
    body: JSON.stringify({ tier }),
  })
}

export function getAdminHealth(): Promise<AdminHealth> {
  return apiFetch<AdminHealth>('/api/v1/admin/health')
}

export function getAdminAgents(params: {
  limit?: number
  offset?: number
  status?: string
  search?: string
}): Promise<AdminAgentList> {
  return apiFetch<AdminAgentList>(`/api/v1/admin/agents${toQueryString(params)}`)
}
