/**
 * Capability registry API client.
 *
 * Maps to:
 *   GET /api/v1/capabilities → listCapabilities
 */

import type { CapabilityDefinition } from '../../types/api'
import { apiFetch } from './client'

/**
 * Fetch all predefined capabilities from the API.
 *
 * Returns capability definitions with endpoint/method mappings
 * that are used for the capability selector dropdown.
 */
export function listCapabilities(): Promise<CapabilityDefinition[]> {
  return apiFetch<CapabilityDefinition[]>('/api/v1/capabilities')
}
