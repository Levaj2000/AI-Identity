/**
 * AI Forensics API — timeline, incident reconstruction, and reports.
 */

import type {
  AuditLogListResponse,
  AuditReconstructResponse,
  AuditStatsResponse,
  ForensicsFilterParams,
  ForensicsReportResponse,
} from '../../types/api'
import { apiFetch, toQueryString } from './client'

/** Fetch paginated audit log entries with optional filters. */
export async function fetchAuditLogs(
  params: ForensicsFilterParams = {},
): Promise<AuditLogListResponse> {
  const qs = toQueryString(params as Record<string, string | number | undefined>)
  return apiFetch<AuditLogListResponse>(`/api/v1/audit${qs}`)
}

/** Fetch aggregated audit statistics for a time window. */
export async function fetchAuditStats(params: {
  agent_id?: string
  start_date?: string
  end_date?: string
}): Promise<AuditStatsResponse> {
  const qs = toQueryString(params)
  return apiFetch<AuditStatsResponse>(`/api/v1/audit/stats${qs}`)
}

/** Reconstruct an incident: events + policy + chain verification. */
export async function fetchAuditReconstruct(params: {
  agent_id: string
  start_date: string
  end_date: string
}): Promise<AuditReconstructResponse> {
  const qs = toQueryString(params)
  return apiFetch<AuditReconstructResponse>(`/api/v1/audit/reconstruct${qs}`)
}

/** Fetch a forensics report as JSON. */
export async function fetchForensicsReport(params: {
  agent_id: string
  start_date: string
  end_date: string
}): Promise<ForensicsReportResponse> {
  const qs = toQueryString({ ...params, format: 'json' })
  return apiFetch<ForensicsReportResponse>(`/api/v1/audit/report${qs}`)
}

/** Download a forensics report as CSV. */
export async function downloadForensicsCSV(params: {
  agent_id: string
  start_date: string
  end_date: string
}): Promise<void> {
  const qs = toQueryString({ ...params, format: 'csv' })
  // Use raw fetch for blob download
  const response = await fetch(`/api/v1/audit/report${qs}`)
  if (!response.ok) throw new Error('Failed to download CSV')

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `forensics-report.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** Verify audit chain integrity. */
export async function verifyAuditChain(agent_id?: string) {
  const qs = agent_id ? toQueryString({ agent_id }) : ''
  return apiFetch<{
    valid: boolean
    total_entries: number
    entries_verified: number
    first_broken_id: number | null
    message: string
  }>(`/api/v1/audit/verify${qs}`)
}
