/**
 * Organization and agent assignment operations.
 */

import type { Organization, OrgMember, AgentAssignment } from '../../types/api'
import { apiFetch } from './client'

const ORG_BASE = '/api/v1/orgs'

export function getMyOrg(): Promise<Organization> {
  return apiFetch<Organization>(`${ORG_BASE}/me`)
}

export function createOrg(name: string): Promise<Organization> {
  return apiFetch<Organization>(ORG_BASE, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function updateOrg(name: string): Promise<Organization> {
  return apiFetch<Organization>(`${ORG_BASE}/me`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  })
}

export function deleteOrg(): Promise<void> {
  return apiFetch<void>(`${ORG_BASE}/me`, { method: 'DELETE' })
}

export function listMembers(): Promise<OrgMember[]> {
  return apiFetch<OrgMember[]>(`${ORG_BASE}/me/members`)
}

export function inviteMember(email: string, role: string = 'member'): Promise<OrgMember> {
  return apiFetch<OrgMember>(`${ORG_BASE}/me/members`, {
    method: 'POST',
    body: JSON.stringify({ email, role }),
  })
}

export function updateMemberRole(userId: string, role: string): Promise<OrgMember> {
  return apiFetch<OrgMember>(`${ORG_BASE}/me/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  })
}

export function removeMember(userId: string): Promise<void> {
  return apiFetch<void>(`${ORG_BASE}/me/members/${userId}`, { method: 'DELETE' })
}

// Forensic verify key
export function getForensicVerifyKey(): Promise<{ forensic_verify_key: string }> {
  return apiFetch<{ forensic_verify_key: string }>(`${ORG_BASE}/me/forensic-verify-key`)
}

export function regenerateForensicVerifyKey(): Promise<{
  forensic_verify_key: string
  warning: string
}> {
  return apiFetch<{ forensic_verify_key: string; warning: string }>(
    `${ORG_BASE}/me/forensic-verify-key/regenerate`,
    { method: 'POST' },
  )
}

// Agent assignments
export function listAgentAssignments(agentId: string): Promise<AgentAssignment[]> {
  return apiFetch<AgentAssignment[]>(`/api/v1/agents/${agentId}/assignments`)
}

export function assignAgent(
  agentId: string,
  userId: string,
  role: string = 'viewer',
): Promise<AgentAssignment> {
  return apiFetch<AgentAssignment>(`/api/v1/agents/${agentId}/assignments`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, role }),
  })
}

export function updateAssignment(
  agentId: string,
  userId: string,
  role: string,
): Promise<AgentAssignment> {
  return apiFetch<AgentAssignment>(`/api/v1/agents/${agentId}/assignments/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  })
}

export function removeAssignment(agentId: string, userId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/agents/${agentId}/assignments/${userId}`, { method: 'DELETE' })
}
