/**
 * Agent key management operations.
 *
 * Maps to:
 *   POST   /api/v1/agents/:id/keys          → createKey
 *   GET    /api/v1/agents/:id/keys          → listKeys
 *   POST   /api/v1/agents/:id/keys/rotate   → rotateKey
 *   DELETE /api/v1/agents/:id/keys/:keyId   → revokeKey
 */

import type {
  AgentKeyCreateResponse,
  AgentKeyListResponse,
  AgentKeyRotateResponse,
  AgentKey,
  KeyStatus,
  KeyType,
} from '../../types/api'
import { apiFetch, toQueryString } from './client'

function keysBase(agentId: string): string {
  return `/api/v1/agents/${agentId}/keys`
}

/**
 * Create a new API key for an agent.
 *
 * Returns the key metadata and a **show-once** plaintext API key.
 *
 * @param agentId - Agent UUID
 * @param keyType - "runtime" (aid_sk_) or "admin" (aid_admin_). Default: runtime
 */
export function createKey(
  agentId: string,
  keyType: KeyType = 'runtime',
): Promise<AgentKeyCreateResponse> {
  const qs = toQueryString({ key_type: keyType })
  return apiFetch<AgentKeyCreateResponse>(`${keysBase(agentId)}${qs}`, {
    method: 'POST',
  })
}

/**
 * List all keys for an agent, optionally filtered by status.
 *
 * @param agentId - Agent UUID
 * @param status  - Filter: active, rotated, or revoked
 */
export function listKeys(agentId: string, status?: KeyStatus): Promise<AgentKeyListResponse> {
  const qs = toQueryString({ status })
  return apiFetch<AgentKeyListResponse>(`${keysBase(agentId)}${qs}`)
}

/**
 * Rotate the agent's active key.
 *
 * Creates a new key and puts the old key into a 24-hour grace period
 * (status=rotated). After 24 hours the old key is automatically revoked.
 *
 * Returns both the new key (with show-once plaintext) and the rotated key.
 */
export function rotateKey(agentId: string): Promise<AgentKeyRotateResponse> {
  return apiFetch<AgentKeyRotateResponse>(`${keysBase(agentId)}/rotate`, {
    method: 'POST',
  })
}

/**
 * Revoke a specific key immediately. This is **irreversible**.
 *
 * @param agentId - Agent UUID
 * @param keyId   - Key ID (integer)
 */
export function revokeKey(agentId: string, keyId: number): Promise<AgentKey> {
  return apiFetch<AgentKey>(`${keysBase(agentId)}/${keyId}`, {
    method: 'DELETE',
  })
}
