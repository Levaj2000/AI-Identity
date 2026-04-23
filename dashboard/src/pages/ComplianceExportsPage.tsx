import { useCallback, useEffect, useState } from 'react'
import { relativeTime } from '../lib/time'
import { createExport, downloadExportAsFile, listExports } from '../services/api/complianceExports'
import { isApiError } from '../services/api/client'
import type { ComplianceExport, ExportProfile, ValidationErrorItem } from '../types/api'

// ─── Profile catalog (labels for dropdown + table) ──────────────

interface ProfileOption {
  value: ExportProfile
  label: string
  nature: 'framework' | 'regulation' | 'voluntary guidance'
}

const PROFILES: readonly ProfileOption[] = [
  { value: 'soc2_tsc_2017', label: 'SOC 2 Type II (TSC 2017)', nature: 'framework' },
  {
    value: 'eu_ai_act_2024',
    label: 'EU AI Act 2024 (high-risk / Annex III)',
    nature: 'regulation',
  },
  {
    value: 'nist_ai_rmf_1_0',
    label: 'NIST AI RMF 1.0',
    nature: 'voluntary guidance',
  },
] as const

function profileLabel(profile: ExportProfile): string {
  return PROFILES.find((p) => p.value === profile)?.label ?? profile
}

// ─── Period helpers ─────────────────────────────────────────────

function defaultPeriodStart(): string {
  // SOC 2 Type II defaults to 12 months; EU AI Act / NIST align on
  // customer-supplied. One year back is the sensible default here.
  const d = new Date()
  d.setUTCFullYear(d.getUTCFullYear() - 1)
  return d.toISOString().slice(0, 10)
}

function defaultPeriodEnd(): string {
  return new Date().toISOString().slice(0, 10)
}

/** Turn a YYYY-MM-DD input into an ISO-8601 UTC timestamp (start-of-day). */
function isoStartOfDay(dateOnly: string): string {
  return `${dateOnly}T00:00:00Z`
}

/** Turn a YYYY-MM-DD input into an ISO-8601 UTC timestamp (end-of-day). */
function isoEndOfDay(dateOnly: string): string {
  return `${dateOnly}T23:59:59Z`
}

// ─── Status styling ────────────────────────────────────────────

function statusBadgeClasses(status: ComplianceExport['status']): string {
  const base = 'rounded-md px-2 py-0.5 text-xs font-medium'
  switch (status) {
    case 'ready':
      return `${base} border border-emerald-200 bg-emerald-100 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300`
    case 'building':
      return `${base} border border-blue-200 bg-blue-100 text-blue-800 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300`
    case 'queued':
      return `${base} border border-amber-200 bg-amber-100 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300`
    case 'failed':
      return `${base} border border-red-200 bg-red-100 text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300`
    default:
      return `${base} border border-gray-200 bg-gray-100 text-gray-600 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#a1a1aa]`
  }
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function mapValidationErrors(errors: ValidationErrorItem[]): Record<string, string> {
  const fieldErrors: Record<string, string> = {}
  for (const err of errors) {
    const field = err.loc[err.loc.length - 1]
    if (typeof field === 'string') {
      fieldErrors[field] = err.msg
    }
  }
  return fieldErrors
}

// ─── Component ─────────────────────────────────────────────────

export function ComplianceExportsPage() {
  const [profile, setProfile] = useState<ExportProfile>('soc2_tsc_2017')
  const [periodStart, setPeriodStart] = useState<string>(defaultPeriodStart())
  const [periodEnd, setPeriodEnd] = useState<string>(defaultPeriodEnd())
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const [exports, setExports] = useState<ComplianceExport[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setListLoading(true)
    setListError(null)
    try {
      const resp = await listExports({ limit: 50 })
      setExports(resp.items)
    } catch (err) {
      setListError(isApiError(err) ? err.message : 'Failed to load exports.')
    } finally {
      setListLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    void refresh()
  }, [refresh])

  // Poll while any job is in-flight so the UI moves queued → building → ready
  // without a manual refresh. Stop once everything settles to avoid chatter.
  useEffect(() => {
    const inFlight = exports.some((e) => e.status === 'queued' || e.status === 'building')
    if (!inFlight) return
    const id = window.setInterval(() => void refresh(), 3000)
    return () => window.clearInterval(id)
  }, [exports, refresh])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setFormError(null)
    setFieldErrors({})
    try {
      await createExport({
        profile,
        audit_period_start: isoStartOfDay(periodStart),
        audit_period_end: isoEndOfDay(periodEnd),
        agent_ids: null,
      })
      await refresh()
    } catch (err) {
      if (isApiError(err)) {
        if (err.validationErrors) {
          setFieldErrors(mapValidationErrors(err.validationErrors))
        }
        setFormError(err.message)
      } else {
        setFormError('Unexpected error — see console for details.')
        // eslint-disable-next-line no-console
        console.error('createExport failed', err)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleDownload = async (exportId: string) => {
    setDownloadingId(exportId)
    try {
      await downloadExportAsFile(exportId)
    } catch (err) {
      setListError(
        err instanceof Error ? err.message : 'Download failed — the archive may have expired.',
      )
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-[#e4e4e7]">
          Compliance Exports
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-gray-600 dark:text-[#a1a1aa]">
          Request a signed, DSSE-chained ZIP bundle of your compliance evidence for a fixed audit
          period. Every artifact in the archive is hash-committed in a manifest signed with the same
          ECDSA P-256 key as forensic attestations — auditors can verify the bundle offline.
        </p>
      </div>

      {/* Request form */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-gray-200 bg-white p-5 dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl"
      >
        <h2 className="mb-3 text-lg font-medium text-gray-900 dark:text-[#e4e4e7]">
          Request a new export
        </h2>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label
              htmlFor="export-profile"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-[#d4d4d8]"
            >
              Framework
            </label>
            <select
              id="export-profile"
              value={profile}
              onChange={(e) => setProfile(e.target.value as ExportProfile)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors focus:border-[#A6DAFF] dark:border-[#2a2a2d] dark:bg-[#04070D] dark:text-[#e4e4e7] dark:focus:border-[#A6DAFF]"
            >
              {PROFILES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-[#71717a]">
              {PROFILES.find((p) => p.value === profile)?.nature}
            </p>
          </div>

          <div>
            <label
              htmlFor="export-period-start"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-[#d4d4d8]"
            >
              Period start (UTC)
            </label>
            <input
              id="export-period-start"
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              required
              className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors dark:bg-[#04070D] dark:text-[#e4e4e7] ${
                fieldErrors.audit_period_start
                  ? 'border-red-500 dark:border-red-500'
                  : 'border-gray-300 focus:border-[#A6DAFF] dark:border-[#2a2a2d] dark:focus:border-[#A6DAFF]'
              }`}
            />
          </div>

          <div>
            <label
              htmlFor="export-period-end"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-[#d4d4d8]"
            >
              Period end (UTC)
            </label>
            <input
              id="export-period-end"
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              required
              className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-900 outline-none transition-colors dark:bg-[#04070D] dark:text-[#e4e4e7] ${
                fieldErrors.audit_period_end
                  ? 'border-red-500 dark:border-red-500'
                  : 'border-gray-300 focus:border-[#A6DAFF] dark:border-[#2a2a2d] dark:focus:border-[#A6DAFF]'
              }`}
            />
          </div>
        </div>

        <p className="mt-3 text-xs text-gray-500 dark:text-[#71717a]">
          Max period: 18 months. Exports are scoped to your org and cover every agent by default —
          narrower sampling plans are not yet exposed here.
        </p>

        {formError && (
          <div
            role="alert"
            className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
          >
            {formError}
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg border border-[#A6DAFF] bg-[#A6DAFF] px-4 py-2 text-sm font-medium text-[#04070D] transition-colors hover:bg-[#A6DAFF]/90 disabled:opacity-50"
          >
            {submitting ? 'Queueing…' : 'Request export'}
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="text-sm text-gray-600 underline-offset-4 transition-colors hover:text-gray-900 hover:underline dark:text-[#a1a1aa] dark:hover:text-[#e4e4e7]"
          >
            Refresh list
          </button>
        </div>
      </form>

      {/* Past exports table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3 dark:border-[#1a1a1d]">
          <h2 className="text-lg font-medium text-gray-900 dark:text-[#e4e4e7]">Recent exports</h2>
          <span className="text-xs text-gray-500 dark:text-[#71717a]">
            {exports.length} {exports.length === 1 ? 'export' : 'exports'}
          </span>
        </div>

        {listError && (
          <div
            role="alert"
            className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
          >
            {listError}
          </div>
        )}

        {listLoading && exports.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-gray-500 dark:text-[#71717a]">
            Loading…
          </div>
        ) : exports.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-gray-500 dark:text-[#71717a]">
            No exports yet. Request your first one above.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-[#1a1a1d]">
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
                  Framework
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
                  Period
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
                  Status
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
                  Size
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
                  Requested
                </th>
                <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#a1a1aa]">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#1a1a1d]/50">
              {exports.map((exp) => (
                <tr
                  key={exp.id}
                  className="transition-colors hover:bg-gray-50 dark:hover:bg-[#1a1a1d]/50"
                >
                  <td className="px-5 py-3 text-gray-900 dark:text-[#e4e4e7]">
                    {profileLabel(exp.profile)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:text-[#a1a1aa]">
                    {exp.audit_period_start.slice(0, 10)} → {exp.audit_period_end.slice(0, 10)}
                  </td>
                  <td className="px-5 py-3">
                    <span className={statusBadgeClasses(exp.status)}>{exp.status}</span>
                    {exp.error && (
                      <p
                        className="mt-1 max-w-xs truncate text-xs text-red-600 dark:text-red-400"
                        title={exp.error.message}
                      >
                        {exp.error.code}
                      </p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 font-[JetBrains_Mono,monospace] text-xs text-gray-600 dark:text-[#a1a1aa]">
                    {formatBytes(exp.archive_bytes)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-xs text-gray-500 dark:text-[#71717a]">
                    {relativeTime(exp.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-right">
                    {exp.status === 'ready' ? (
                      <button
                        onClick={() => void handleDownload(exp.id)}
                        disabled={downloadingId === exp.id}
                        className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#d4d4d8] dark:hover:bg-[#2a2a2d]"
                      >
                        {downloadingId === exp.id ? 'Downloading…' : 'Download'}
                      </button>
                    ) : (
                      <span className="text-xs text-gray-400 dark:text-[#52525b]">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
