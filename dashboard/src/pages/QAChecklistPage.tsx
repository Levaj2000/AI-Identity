import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import {
  triggerQARun,
  triggerOnboardingRun,
  listQARuns,
  signoffQARun,
  type QARun,
  type QACheck,
} from '../services/api/qa'

// ── Section grouping ─────────────────────────────────────────────

const SECTIONS = [
  'Health & Infrastructure',
  'Authentication & Agent Lifecycle',
  'Gateway Policy Enforcement',
  'Audit & Compliance',
  'Key Management & Cleanup',
]

function groupChecks(checks: QACheck[]): Record<string, QACheck[]> {
  const grouped: Record<string, QACheck[]> = {}
  for (const s of SECTIONS) grouped[s] = []
  for (const c of checks) {
    if (grouped[c.section]) grouped[c.section].push(c)
    else grouped[c.section] = [c]
  }
  return grouped
}

// ── Status badge ─────────────────────────────────────────────────

function StatusBadge({ passed }: { passed: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        passed ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'
      }`}
    >
      {passed ? 'PASS' : 'FAIL'}
    </span>
  )
}

// ── Acceptance record (print → PDF) ──────────────────────────────

/**
 * Open a clean, light, print-friendly acceptance certificate in a new
 * window and trigger the browser's print dialog (→ Save as PDF). No PDF
 * dependency — the rendered certificate is the artifact, bound to the run id
 * and both signatures.
 */
function downloadAcceptanceRecord(run: QARun): void {
  const checks = run.results?.checks || []
  const grouped = groupChecks(checks)
  const fmt = (s: string | null) => (s ? new Date(s).toLocaleString() : '—')

  const sectionRows = SECTIONS.map((section) => {
    const c = grouped[section] || []
    if (c.length === 0) return ''
    const passed = c.filter((x) => x.passed).length
    const ok = passed === c.length
    return `<tr>
      <td>${section}</td>
      <td style="text-align:right;color:${ok ? '#15803d' : '#b91c1c'};font-weight:600;">${passed} / ${c.length}</td>
    </tr>`
  }).join('')

  const sig = (label: string, by: string | null, at: string | null) => `
    <div class="sig">
      <div class="sig-name">${by || '—'}</div>
      <div class="sig-rule"></div>
      <div class="sig-label">${label}</div>
      <div class="sig-date">${fmt(at)}</div>
    </div>`

  const html = `<!doctype html><html><head><meta charset="utf-8" />
    <title>Onboarding acceptance — ${run.run_id}</title>
    <style>
      *{box-sizing:border-box} body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;margin:0;padding:48px;}
      .wrap{max-width:720px;margin:0 auto;}
      .brand{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#185fa5;}
      h1{font-size:26px;margin:6px 0 2px;font-weight:600;}
      .sub{color:#64748b;font-size:14px;margin-bottom:24px;}
      .verdict{display:inline-block;border:1.5px solid #185fa5;color:#185fa5;border-radius:999px;padding:8px 16px;font-weight:600;font-size:15px;margin-bottom:24px;}
      table{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px;}
      td{padding:9px 0;border-bottom:1px solid #e2e8f0;}
      .meta{font-size:13px;color:#475569;line-height:1.9;margin-bottom:24px;}
      .meta b{color:#0f172a;font-weight:600;}
      .sigs{display:flex;gap:32px;margin-top:36px;}
      .sig{flex:1;}
      .sig-name{font-family:Georgia,'Times New Roman',serif;font-size:22px;min-height:30px;color:#0f172a;}
      .sig-rule{border-bottom:1px solid #0f172a;margin:4px 0 8px;}
      .sig-label{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#64748b;}
      .sig-date{font-size:12px;color:#94a3b8;margin-top:2px;}
      .foot{margin-top:40px;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:12px;}
    </style></head><body><div class="wrap">
      <div class="brand">AI Identity · onboarding acceptance</div>
      <h1>${run.run_id}</h1>
      <div class="sub">Two-party acceptance record</div>
      <div class="verdict">${run.passed_count} / ${run.total_count} checks ${run.status === 'passed' ? 'passed' : 'with issues'}</div>
      <div class="meta">
        <div><b>Ran as:</b> ${run.run_by}</div>
        <div><b>Environment:</b> ${run.environment}</div>
        <div><b>Completed:</b> ${fmt(run.created_at)} · ${(run.duration_ms / 1000).toFixed(1)}s</div>
      </div>
      <table>${sectionRows}</table>
      <div class="sigs">
        ${sig('Customer', run.customer_signoff_by, run.customer_signoff_at)}
        ${sig('AI Identity staff', run.staff_signoff_by, run.staff_signoff_at)}
      </div>
      <div class="foot">Both signatures bind to run ${run.run_id}. Generated ${new Date().toLocaleString()}.</div>
    </div>
    <script>window.onload=function(){window.print()}</script>
    </body></html>`

  const w = window.open('', '_blank', 'width=820,height=900')
  if (!w) return
  w.document.write(html)
  w.document.close()
}

// ── Signature card ───────────────────────────────────────────────

function SignatureCard({
  label,
  by,
  at,
  canSign,
  signing,
  onSign,
}: {
  label: string
  by: string | null
  at: string | null
  canSign: boolean
  signing: boolean
  onSign: () => void
}) {
  const signed = !!by
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="mb-2.5 flex items-center justify-between">
        <span className="text-xs text-subtle">{label}</span>
        {signed ? (
          <span className="inline-flex items-center gap-1 text-xs text-success">
            <span className="h-1.5 w-1.5 rounded-full bg-success" /> Signed
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-warning">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" /> Awaiting
          </span>
        )}
      </div>
      <div
        className={`border-b pb-2 font-serif text-xl ${
          signed ? 'border-line-strong text-ink' : 'border-dashed border-line-strong text-faint'
        }`}
      >
        {signed ? by : 'Sign to accept'}
      </div>
      <p className="mt-2 text-xs text-subtle">
        {signed && at ? new Date(at).toLocaleString() : 'Countersign to issue the certificate'}
      </p>
      {!signed && canSign && (
        <button
          onClick={onSign}
          disabled={signing}
          className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-brand px-3 py-1.5 text-xs font-medium text-brand hover:bg-brand-soft disabled:opacity-50"
        >
          {signing ? 'Signing...' : `Sign off as ${label}`}
        </button>
      )}
    </div>
  )
}

// ── Check detail row ─────────────────────────────────────────────

function CheckRow({ check }: { check: QACheck }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={`border-l-2 py-2 pl-4 ${check.passed ? 'border-success' : 'border-danger'}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-faint w-6">{check.step}</span>
          <span className="text-sm text-muted">{check.name}</span>
          <StatusBadge passed={check.passed} />
        </div>
        <span className="text-xs text-faint">
          {check.duration_ms}ms
          <span className="ml-2">{expanded ? '▾' : '▸'}</span>
        </span>
      </button>
      {expanded && (
        <div className="mt-2 ml-9 space-y-1">
          <p className="text-xs text-subtle font-mono">{check.details}</p>
          {check.error && <p className="text-xs text-danger font-mono">Error: {check.error}</p>}
        </div>
      )}
    </div>
  )
}

// ── Run detail panel ─────────────────────────────────────────────

function RunDetail({
  run,
  onSignoff,
  signingOff,
}: {
  run: QARun
  onSignoff: (role: 'customer' | 'staff') => void
  signingOff: boolean
}) {
  const { user } = useAuth()
  const [showLog, setShowLog] = useState(false)
  const checks = run.results?.checks || []
  const grouped = groupChecks(checks)

  const fullySignedOff = !!run.customer_signoff_by && !!run.staff_signoff_by
  const passed = run.status === 'passed'

  return (
    <div className="space-y-5">
      {/* Header + export */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-ink">Onboarding acceptance</h3>
            <span className="rounded-full bg-elevated px-2.5 py-0.5 text-xs font-medium text-subtle">
              {run.mode === 'onboarding' ? 'Partner run' : 'Admin check'}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-subtle">
            Two-party validation that onboarding succeeded — both sign to accept
          </p>
        </div>
        <button
          onClick={() => downloadAcceptanceRecord(run)}
          className="flex shrink-0 items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-ink hover:bg-brand-hover"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
            <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
            <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
          </svg>
          Download signed PDF
        </button>
      </div>

      {/* Certificate hero */}
      <div className="border-l-[3px] border-brand bg-inset p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-subtle">Ran as</div>
            <div className="mt-1 text-lg font-semibold text-ink">{run.run_by}</div>
            <div className="mt-1 font-mono text-xs text-muted">
              {run.run_id} · {run.environment} · {(run.duration_ms / 1000).toFixed(1)}s
            </div>
          </div>
          <div className="text-right">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium ${
                passed ? 'bg-brand-soft text-brand ring-1 ring-brand' : 'bg-danger-soft text-danger'
              }`}
            >
              {run.passed_count} / {run.total_count} checks {passed ? 'passed' : 'with issues'}
            </span>
            <div className="mt-1.5 text-xs text-subtle">
              {new Date(run.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Section summary */}
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {SECTIONS.map((section) => {
          const c = grouped[section] || []
          if (c.length === 0) return null
          const p = c.filter((x) => x.passed).length
          const ok = p === c.length
          return (
            <div key={section} className="rounded-lg border border-line bg-surface p-3">
              <div className="text-xs text-muted">{section}</div>
              <div className={`mt-1.5 text-xs font-medium ${ok ? 'text-success' : 'text-danger'}`}>
                {p} / {c.length} pass
              </div>
            </div>
          )
        })}
      </div>

      {/* Acceptance signatures */}
      <div>
        <div className="mb-2.5 text-[11px] uppercase tracking-wider text-subtle">
          Acceptance signatures
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <SignatureCard
            label="Customer"
            by={run.customer_signoff_by}
            at={run.customer_signoff_at}
            canSign={!!user}
            signing={signingOff}
            onSign={() => onSignoff('customer')}
          />
          <SignatureCard
            label="AI Identity staff"
            by={run.staff_signoff_by}
            at={run.staff_signoff_at}
            canSign={!!user}
            signing={signingOff}
            onSign={() => onSignoff('staff')}
          />
        </div>
        {fullySignedOff && (
          <div className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand">
            <span className="h-1.5 w-1.5 rounded-full bg-brand" />
            Fully validated — both parties signed
          </div>
        )}
      </div>

      {/* Full check log (evidence) */}
      <div>
        <button
          onClick={() => setShowLog((v) => !v)}
          className="flex items-center gap-1.5 text-sm text-muted hover:text-ink"
        >
          <span>{showLog ? '▾' : '▸'}</span>
          {showLog ? 'Hide' : 'View'} full check log ({checks.length} steps)
        </button>
        {showLog && (
          <div className="mt-3 space-y-4">
            {SECTIONS.map((section) => {
              const sectionChecks = grouped[section] || []
              if (sectionChecks.length === 0) return null
              const allPassed = sectionChecks.every((c) => c.passed)
              return (
                <div key={section}>
                  <div className="mb-2 flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-muted">{section}</h4>
                    <StatusBadge passed={allPassed} />
                  </div>
                  <div className="space-y-1 rounded-lg border border-line bg-inset p-3">
                    {sectionChecks.map((check) => (
                      <CheckRow key={check.step} check={check} />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────

export function QAChecklistPage() {
  const [runs, setRuns] = useState<QARun[]>([])
  const [selectedRun, setSelectedRun] = useState<QARun | null>(null)
  const [running, setRunning] = useState(false)
  const [signingOff, setSigningOff] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRuns()
  }, [])

  async function loadRuns() {
    try {
      const data = await listQARuns(20)
      setRuns(data.items)
      if (data.items.length > 0 && !selectedRun) {
        setSelectedRun(data.items[0])
      }
    } catch {
      setError('Failed to load QA runs')
    } finally {
      setLoading(false)
    }
  }

  async function handleRunQA(mode: 'admin' | 'onboarding' = 'admin') {
    setRunning(true)
    setError(null)
    try {
      const run = mode === 'onboarding' ? await triggerOnboardingRun() : await triggerQARun()
      setSelectedRun(run)
      setRuns((prev) => [run, ...prev])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'QA run failed')
    } finally {
      setRunning(false)
    }
  }

  async function handleSignoff(role: 'customer' | 'staff') {
    if (!selectedRun) return
    setSigningOff(true)
    try {
      const updated = await signoffQARun(selectedRun.run_id, role)
      setSelectedRun(updated)
      setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
    } catch {
      setError('Sign-off failed')
    } finally {
      setSigningOff(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Onboarding acceptance</h1>
          <p className="text-sm text-subtle">
            15-step E2E validation, dual-signed by the customer and AI Identity
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleRunQA('onboarding')}
            disabled={running}
            className="flex items-center gap-2 rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-brand-ink hover:bg-brand-hover disabled:opacity-50 transition-colors"
          >
            {running ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Running...
              </>
            ) : (
              <>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
                </svg>
                Run onboarding acceptance
              </>
            )}
          </button>
          <button
            onClick={() => handleRunQA('admin')}
            disabled={running}
            className="flex items-center gap-2 rounded-lg border border-brand px-5 py-2.5 text-sm font-medium text-brand hover:bg-brand-soft disabled:opacity-50 transition-colors"
          >
            {running ? (
              'Running...'
            ) : (
              <>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm6.39-2.908a.75.75 0 01.766.027l3.5 2.25a.75.75 0 010 1.262l-3.5 2.25A.75.75 0 018 12.25v-4.5a.75.75 0 01.39-.658z"
                    clipRule="evenodd"
                  />
                </svg>
                Admin check
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Run history sidebar */}
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-muted">Run history</h2>
          {loading ? (
            <p className="text-sm text-faint">Loading...</p>
          ) : runs.length === 0 ? (
            <p className="text-sm text-faint">
              No runs yet. Run an onboarding acceptance to start.
            </p>
          ) : (
            <div className="space-y-1">
              {runs.map((run) => {
                const isSelected = selectedRun?.id === run.id
                const fullySignedOff = !!run.customer_signoff_by && !!run.staff_signoff_by
                return (
                  <button
                    key={run.id}
                    onClick={() => setSelectedRun(run)}
                    className={`w-full rounded-lg px-3 py-2.5 text-left transition-colors ${
                      isSelected ? 'bg-brand-soft ring-1 ring-brand' : 'hover:bg-elevated'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-muted">{run.run_id}</span>
                      <span
                        className={`text-xs font-medium ${
                          run.status === 'passed' ? 'text-success' : 'text-danger'
                        }`}
                      >
                        {run.passed_count}/{run.total_count}
                      </span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="text-xs text-faint">
                        {new Date(run.created_at).toLocaleDateString()}
                      </span>
                      {run.mode === 'onboarding' && (
                        <span className="text-xs text-brand">Onboarding</span>
                      )}
                      {fullySignedOff && <span className="text-xs text-brand">Validated</span>}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Run detail */}
        <div className="rounded-xl border border-line bg-surface p-6">
          {selectedRun ? (
            <RunDetail run={selectedRun} onSignoff={handleSignoff} signingOff={signingOff} />
          ) : (
            <div className="flex h-64 items-center justify-center text-faint">
              <p>Run an onboarding acceptance to see results here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
