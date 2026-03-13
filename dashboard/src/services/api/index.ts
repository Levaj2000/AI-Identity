/**
 * API client — barrel export.
 *
 * Usage:
 *   import { createAgent, listKeys, isApiError } from '@/services/api'
 */

export { apiFetch, getApiKey, setApiKey, clearApiKey, isApiError, toQueryString } from './client'
export { createAgent, listAgents, getAgent, updateAgent, deleteAgent } from './agents'
export { createKey, listKeys, rotateKey, revokeKey } from './keys'
