/**
 * API client — barrel export.
 *
 * Usage:
 *   import { createAgent, listKeys, isApiError } from '@/services/api'
 */

export { apiFetch, getApiKey, setApiKey, clearApiKey, isApiError, toQueryString } from './client'
export { createAgent, listAgents, getAgent, updateAgent, deleteAgent } from './agents'
export { createKey, listKeys, rotateKey, revokeKey } from './keys'
export {
  fetchAuditLogs,
  fetchAuditStats,
  fetchAuditReconstruct,
  fetchForensicsReport,
  downloadForensicsCSV,
  verifyAuditChain,
} from './forensics'
export {
  getMyOrg,
  createOrg,
  updateOrg,
  deleteOrg,
  listMembers,
  inviteMember,
  updateMemberRole,
  removeMember,
  listAgentAssignments,
  assignAgent,
  updateAssignment,
  removeAssignment,
} from './organizations'
