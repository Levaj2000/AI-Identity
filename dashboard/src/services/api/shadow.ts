/**
 * Shadow Agent Detection API client.
 */

import { apiFetch, toQueryString } from './client'

// ── Types ───────────────────────────────────────────────────────────

export interface ShadowAgentStats {
  total_shadow_agents: number
  total_shadow_hits: number
  agents_not_found: number
  agents_inactive: number
  agents_blocked: number
  agents_dismissed: number
}

export interface ShadowAgentSummary {
  agent_id: string
  deny_reason: string
  hit_count: number
  first_seen: string
  last_seen: string
  top_endpoints: string[]
  is_blocked: boolean
  is_dismissed: boolean
}

export interface ShadowAgentList {
  items: ShadowAgentSummary[]
  total: number
  total_hits: number
  limit: number
  offset: number
}

export interface TopEndpointHit {
  endpoint: string
  method: string
  count: number
}

export interface ShadowEvent {
  id: number
  endpoint: string
  method: string
  deny_reason: string
  request_metadata: Record<string, unknown>
  created_at: string | null
}

export interface ShadowAgentDetail {
  agent_id: string
  deny_reason: string
  hit_count: number
  first_seen: string
  last_seen: string
  top_endpoints: TopEndpointHit[]
  recent_events: ShadowEvent[]
  is_blocked: boolean
  blocked_at: string | null
  is_dismissed: boolean
}

export interface BlockAgentResponse {
  agent_id: string
  blocked: boolean
  blocked_at: string
}

export interface DismissResponse {
  agent_id: string
  dismissed: boolean
}

// ── API Functions ───────────────────────────────────────────────────

export function getShadowAgentStats(params?: {
  start_date?: string
  end_date?: string
}): Promise<ShadowAgentStats> {
  return apiFetch<ShadowAgentStats>(`/api/v1/shadow-agents/stats${toQueryString(params || {})}`)
}

export function getShadowAgents(params: {
  limit?: number
  offset?: number
  start_date?: string
  end_date?: string
  min_hits?: number
  deny_reason?: string
  include_dismissed?: boolean
}): Promise<ShadowAgentList> {
  return apiFetch<ShadowAgentList>(`/api/v1/shadow-agents${toQueryString(params)}`)
}

export function getShadowAgentDetail(
  agentId: string,
  params?: { start_date?: string; end_date?: string },
): Promise<ShadowAgentDetail> {
  return apiFetch<ShadowAgentDetail>(
    `/api/v1/shadow-agents/${agentId}${toQueryString(params || {})}`,
  )
}

export function blockShadowAgent(agentId: string, reason?: string): Promise<BlockAgentResponse> {
  return apiFetch<BlockAgentResponse>(`/api/v1/shadow-agents/${agentId}/block`, {
    method: 'POST',
    body: JSON.stringify(reason ? { reason } : {}),
  })
}

export function unblockShadowAgent(agentId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/shadow-agents/${agentId}/block`, { method: 'DELETE' })
}

export function dismissShadowAgent(agentId: string): Promise<DismissResponse> {
  return apiFetch<DismissResponse>(`/api/v1/shadow-agents/${agentId}/dismiss`, { method: 'POST' })
}

export function undismissShadowAgent(agentId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/shadow-agents/${agentId}/dismiss`, { method: 'DELETE' })
}
