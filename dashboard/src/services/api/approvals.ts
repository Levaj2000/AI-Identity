/**
 * Approvals API client — human-in-the-loop review for enterprise tier.
 */

import { apiFetch, toQueryString } from './client'

// ── Types ───────────────────────────────────────────────────────────

export interface Approval {
  id: string
  agent_id: string
  agent_name: string | null
  user_id: string
  endpoint: string
  method: string
  request_metadata: Record<string, unknown>
  status: string
  reviewer_id: string | null
  reviewer_note: string | null
  resolved_at: string | null
  expires_at: string
  created_at: string | null
  updated_at: string | null
}

export interface ApprovalList {
  items: Approval[]
  total: number
  limit: number
  offset: number
}

export interface ApprovalPendingCount {
  count: number
}

// ── API Functions ───────────────────────────────────────────────────

export function getApprovals(params: {
  limit?: number
  offset?: number
  status?: string
  agent_id?: string
}): Promise<ApprovalList> {
  return apiFetch<ApprovalList>(`/api/v1/approvals${toQueryString(params)}`)
}

export function getApprovalDetail(id: string): Promise<Approval> {
  return apiFetch<Approval>(`/api/v1/approvals/${id}`)
}

export function resolveApproval(
  id: string,
  action: 'approve' | 'reject',
  note?: string,
): Promise<Approval> {
  return apiFetch<Approval>(`/api/v1/approvals/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ action, note: note || undefined }),
  })
}

export function getPendingCount(): Promise<ApprovalPendingCount> {
  return apiFetch<ApprovalPendingCount>('/api/v1/approvals/pending/count')
}
