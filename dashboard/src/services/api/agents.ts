/**
 * Agent CRUD operations.
 *
 * Maps to:
 *   POST   /api/v1/agents              → createAgent
 *   GET    /api/v1/agents              → listAgents
 *   GET    /api/v1/agents/:id          → getAgent
 *   PUT    /api/v1/agents/:id          → updateAgent
 *   DELETE /api/v1/agents/:id          → deleteAgent
 */

import type {
  Agent,
  AgentCreate,
  AgentCreateResponse,
  AgentListParams,
  AgentListResponse,
  AgentUpdate,
} from '../../types/api'
import { apiFetch, toQueryString } from './client'

const BASE = '/api/v1/agents'

/**
 * Create a new agent.
 *
 * Returns the agent and a **show-once** plaintext API key.
 * Store the key securely — it cannot be retrieved again.
 */
export function createAgent(data: AgentCreate): Promise<AgentCreateResponse> {
  return apiFetch<AgentCreateResponse>(BASE, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * List agents with optional filters and pagination.
 *
 * @param params.status  - Filter by status: active, suspended, revoked
 * @param params.capability - Filter by capability string
 * @param params.limit   - Max items per page (default: 50)
 * @param params.offset  - Number of items to skip (default: 0)
 */
export function listAgents(params: AgentListParams = {}): Promise<AgentListResponse> {
  const qs = toQueryString(params as Record<string, string | number | boolean | undefined>)
  return apiFetch<AgentListResponse>(`${BASE}${qs}`)
}

/**
 * Get a single agent by ID.
 */
export function getAgent(agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`${BASE}/${agentId}`)
}

/**
 * Update an agent. Only include fields you want to change.
 *
 * To suspend an agent, pass `{ status: 'suspended' }`.
 * To revoke, use `deleteAgent()` instead (irreversible).
 */
export function updateAgent(agentId: string, data: AgentUpdate): Promise<Agent> {
  return apiFetch<Agent>(`${BASE}/${agentId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

/**
 * Revoke (soft-delete) an agent. This is **irreversible**.
 *
 * Sets agent status to "revoked" and revokes all associated keys.
 */
export function deleteAgent(agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`${BASE}/${agentId}`, {
    method: 'DELETE',
  })
}
