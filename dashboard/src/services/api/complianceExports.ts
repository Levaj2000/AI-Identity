/**
 * Compliance export API client.
 *
 * Maps to:
 *   POST /api/v1/exports              → createExport
 *   GET  /api/v1/exports              → listExports
 *   GET  /api/v1/exports/:id          → getExport
 *   GET  /api/v1/exports/:id/download → downloadExport (blob)
 *
 * Backend contract: `docs/ADR-002-compliance-exports.md`.
 * The builder is async — POST returns 202 with status=queued; poll
 * GET until status=ready, then fetch the signed archive via download.
 */

import type {
  ComplianceExport,
  ComplianceExportListResponse,
  ExportCreateRequest,
  ExportProfile,
  ExportStatus,
} from '../../types/api'
import { apiFetch, getApiBaseUrl, getAuthHeaders, toQueryString } from './client'

const BASE = '/api/v1/exports'

/** Create (queue) a new export build. Returns the queued job. */
export function createExport(data: ExportCreateRequest): Promise<ComplianceExport> {
  return apiFetch<ComplianceExport>(BASE, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export interface ListExportsParams {
  profile?: ExportProfile
  status?: ExportStatus
  limit?: number
  before?: string
}

/** List export jobs for the caller's org, newest first. */
export function listExports(params: ListExportsParams = {}): Promise<ComplianceExportListResponse> {
  const qs = toQueryString(params as Record<string, string | number | boolean | undefined>)
  return apiFetch<ComplianceExportListResponse>(`${BASE}${qs}`)
}

/** Fetch a single export job by id — used to poll status. */
export function getExport(exportId: string): Promise<ComplianceExport> {
  return apiFetch<ComplianceExport>(`${BASE}/${exportId}`)
}

/**
 * Cancel a queued or building export.
 *
 * Transitions the job to `failed` with `error_code=cancelled`.
 * 409s with `export_not_cancellable` if the job is already terminal
 * (ready / failed) — the UI should disable the button in those states
 * so that path is defensive, not expected.
 */
export function cancelExport(exportId: string): Promise<ComplianceExport> {
  return apiFetch<ComplianceExport>(`${BASE}/${exportId}/cancel`, {
    method: 'POST',
  })
}

/**
 * Download the archive ZIP for a ready export.
 *
 * Raw fetch because the response is binary — `apiFetch` assumes JSON
 * and would blow up on the body. Auth headers still come from the
 * same Clerk/legacy path so no duplication of credential logic.
 */
export async function downloadExport(exportId: string): Promise<Blob> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${getApiBaseUrl()}${BASE}/${exportId}/download`, {
    headers,
  })
  if (!response.ok) {
    throw new Error(`download failed: ${response.status} ${response.statusText}`)
  }
  return response.blob()
}

/**
 * Convenience helper: download + trigger a browser save with the
 * canonical filename. Pulls the blob via `downloadExport` so auth +
 * API base URL stay centralised.
 */
export async function downloadExportAsFile(exportId: string): Promise<void> {
  const blob = await downloadExport(exportId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `export-${exportId}.zip`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
