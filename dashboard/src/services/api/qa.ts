/**
 * QA Checklist API service — trigger runs, list results, sign off.
 */

import { apiFetch } from './client'

const BASE = '/api/v1/qa'

// ── Types ────────────────────────────────────────────────────────

export interface QACheck {
  step: number
  name: string
  section: string
  passed: boolean
  duration_ms: number
  details: string
  error: string | null
}

export interface QARunResults {
  checks: QACheck[]
  passed: number
  failed: number
  total: number
  duration_ms: number
  all_passed: boolean
}

export interface QARun {
  id: number
  status: string
  run_by: string
  environment: string
  duration_ms: number
  passed_count: number
  failed_count: number
  total_count: number
  results: QARunResults
  customer_signoff_by: string | null
  customer_signoff_at: string | null
  customer_signoff_note: string | null
  staff_signoff_by: string | null
  staff_signoff_at: string | null
  staff_signoff_note: string | null
  created_at: string
}

export interface QARunListResponse {
  items: QARun[]
  total: number
}

// ── API calls ────────────────────────────────────────────────────

export function triggerQARun(): Promise<QARun> {
  return apiFetch<QARun>(`${BASE}/run`, { method: 'POST' })
}

export function listQARuns(limit = 20, offset = 0): Promise<QARunListResponse> {
  return apiFetch<QARunListResponse>(`${BASE}/runs?limit=${limit}&offset=${offset}`)
}

export function getQARun(runId: number): Promise<QARun> {
  return apiFetch<QARun>(`${BASE}/runs/${runId}`)
}

export function signoffQARun(
  runId: number,
  role: 'customer' | 'staff',
  note?: string,
): Promise<QARun> {
  return apiFetch<QARun>(`${BASE}/runs/${runId}/signoff`, {
    method: 'POST',
    body: JSON.stringify({ role, note: note || null }),
  })
}
