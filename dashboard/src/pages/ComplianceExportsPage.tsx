import { useCallback, useEffect, useState } from 'react'
import { ConfirmModal } from '../components/modals/ConfirmModal'
import { relativeTime } from '../lib/time'
import {
  cancelExport,
  createExport,
  downloadExportAsFile,
  listExports,
} from '../services/api/complianceExports'
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
      return `${base} border border-success bg-success-soft text-success`
    case 'building':
      return `${base} border border-brand bg-brand-soft text-brand`
    case 'queued':
      return `${base} border border-warning bg-warning-soft text-warning`
    case 'failed':
      return `${base} border border-danger bg-danger-soft text-danger`
    default:
      return `${base} border border-line-strong bg-elevated text-muted`
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

  // Cancel flow — two-step with a confirm modal so a misclick on the
  // row doesn't nuke an actively-building export.
  const [cancelTarget, setCancelTarget] = useState<ComplianceExport | null>(null)
  const [cancelling, setCancelling] = useState(false)

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

  const handleCancelConfirm = async () => {
    if (!cancelTarget) return
    setCancelling(true)
    try {
      await cancelExport(cancelTarget.id)
      setCancelTarget(null)
      await refresh()
    } catch (err) {
      setListError(isApiError(err) ? err.message : 'Cancel failed.')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Compliance Exports</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">
          Request a signed, DSSE-chained ZIP bundle of your compliance evidence for a fixed audit
          period. Every artifact in the archive is hash-committed in a manifest signed with the same
          ECDSA P-256 key as forensic attestations — auditors can verify the bundle offline.
        </p>
      </div>

      {/* Request form */}
      <form onSubmit={handleSubmit} className="rounded-xl border border-line bg-surface p-5">
        <h2 className="mb-3 text-lg font-medium text-ink">Request a new export</h2>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="export-profile" className="mb-1.5 block text-sm font-medium text-muted">
              Framework
            </label>
            <select
              id="export-profile"
              value={profile}
              onChange={(e) => setProfile(e.target.value as ExportProfile)}
              className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-brand"
            >
              {PROFILES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-subtle">
              {PROFILES.find((p) => p.value === profile)?.nature}
            </p>
          </div>

          <div>
            <label
              htmlFor="export-period-start"
              className="mb-1.5 block text-sm font-medium text-muted"
            >
              Period start (UTC)
            </label>
            <input
              id="export-period-start"
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              required
              className={`w-full rounded-lg border bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors ${
                fieldErrors.audit_period_start
                  ? 'border-danger'
                  : 'border-line-strong focus:border-brand'
              }`}
            />
          </div>

          <div>
            <label
              htmlFor="export-period-end"
              className="mb-1.5 block text-sm font-medium text-muted"
            >
              Period end (UTC)
            </label>
            <input
              id="export-period-end"
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              required
              className={`w-full rounded-lg border bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors ${
                fieldErrors.audit_period_end
                  ? 'border-danger'
                  : 'border-line-strong focus:border-brand'
              }`}
            />
          </div>
        </div>

        <p className="mt-3 text-xs text-subtle">
          Max period: 18 months. Exports are scoped to your org and cover every agent by default —
          narrower sampling plans are not yet exposed here.
        </p>

        {formError && (
          <div
            role="alert"
            className="mt-3 rounded-lg border border-danger bg-danger-soft px-3 py-2 text-sm text-danger"
          >
            {formError}
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg border border-brand bg-brand px-4 py-2 text-sm font-medium text-brand-ink transition-colors hover:bg-brand-hover disabled:opacity-50"
          >
            {submitting ? 'Queueing…' : 'Request export'}
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="text-sm text-muted underline-offset-4 transition-colors hover:text-ink hover:underline"
          >
            Refresh list
          </button>
        </div>
      </form>

      {/* Past exports table */}
      <div className="overflow-hidden rounded-xl border border-line bg-surface">
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <h2 className="text-lg font-medium text-ink">Recent exports</h2>
          <span className="text-xs text-subtle">
            {exports.length} {exports.length === 1 ? 'export' : 'exports'}
          </span>
        </div>

        {listError && (
          <div
            role="alert"
            className="border-b border-danger bg-danger-soft px-5 py-3 text-sm text-danger"
          >
            {listError}
          </div>
        )}

        {listLoading && exports.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-subtle">Loading…</div>
        ) : exports.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-subtle">
            No exports yet. Request your first one above.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line">
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Framework
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Period
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Status
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Size
                </th>
                <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-subtle">
                  Requested
                </th>
                <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wider text-subtle">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {exports.map((exp) => (
                <tr key={exp.id} className="transition-colors hover:bg-elevated">
                  <td className="px-5 py-3 text-ink">{profileLabel(exp.profile)}</td>
                  <td className="whitespace-nowrap px-5 py-3 font-[JetBrains_Mono,monospace] text-xs text-muted">
                    {exp.audit_period_start.slice(0, 10)} → {exp.audit_period_end.slice(0, 10)}
                  </td>
                  <td className="px-5 py-3">
                    <span className={statusBadgeClasses(exp.status)}>{exp.status}</span>
                    {exp.error && (
                      <p
                        className="mt-1 max-w-xs truncate text-xs text-danger"
                        title={exp.error.message}
                      >
                        {exp.error.code}
                      </p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 font-[JetBrains_Mono,monospace] text-xs text-muted">
                    {formatBytes(exp.archive_bytes)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-xs text-subtle">
                    {relativeTime(exp.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-right">
                    {exp.status === 'ready' ? (
                      <button
                        onClick={() => void handleDownload(exp.id)}
                        disabled={downloadingId === exp.id}
                        className="rounded-md border border-line-strong bg-surface px-2.5 py-1 text-xs font-medium text-muted transition-colors hover:bg-elevated disabled:opacity-50"
                      >
                        {downloadingId === exp.id ? 'Downloading…' : 'Download'}
                      </button>
                    ) : exp.status === 'queued' || exp.status === 'building' ? (
                      <button
                        onClick={() => setCancelTarget(exp)}
                        className="rounded-md border border-danger bg-surface px-2.5 py-1 text-xs font-medium text-danger transition-colors hover:bg-danger-soft disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    ) : (
                      <span className="text-xs text-faint">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {cancelTarget && (
        <ConfirmModal
          title="Cancel export?"
          message={
            cancelTarget.status === 'building'
              ? 'This export is currently building. Cancelling marks it as failed — the archive (if any work has been done) is discarded. You can request a fresh export with the same scope immediately after.'
              : 'This export is queued but not yet started. Cancelling removes it from the queue so you can request a new one with the same scope.'
          }
          confirmLabel="Cancel export"
          confirmVariant="danger"
          isLoading={cancelling}
          onConfirm={() => void handleCancelConfirm()}
          onCancel={() => setCancelTarget(null)}
        />
      )}
    </div>
  )
}
