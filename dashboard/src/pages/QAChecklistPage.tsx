import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import {
  triggerQARun,
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
        passed
          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
      }`}
    >
      {passed ? 'PASS' : 'FAIL'}
    </span>
  )
}

// ── Signoff badge ────────────────────────────────────────────────

function SignoffBadge({ label, by, at }: { label: string; by: string | null; at: string | null }) {
  if (!by) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-500 dark:bg-[#1a1a1d] dark:text-[#52525b]">
        <span className="h-2 w-2 rounded-full bg-gray-300 dark:bg-[#3f3f46]" />
        {label}: Pending
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
      <span className="h-2 w-2 rounded-full bg-green-500" />
      {label}: {by}
      {at && (
        <span className="text-green-600 dark:text-green-500">
          {' '}
          ({new Date(at).toLocaleDateString()})
        </span>
      )}
    </span>
  )
}

// ── Check detail row ─────────────────────────────────────────────

function CheckRow({ check }: { check: QACheck }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`border-l-2 py-2 pl-4 ${
        check.passed
          ? 'border-green-400 dark:border-green-600'
          : 'border-red-400 dark:border-red-600'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-gray-400 dark:text-[#52525b] w-6">
            {check.step}
          </span>
          <span className="text-sm text-gray-700 dark:text-[#e4e4e7]">{check.name}</span>
          <StatusBadge passed={check.passed} />
        </div>
        <span className="text-xs text-gray-400 dark:text-[#52525b]">
          {check.duration_ms}ms
          <span className="ml-2">{expanded ? '▾' : '▸'}</span>
        </span>
      </button>
      {expanded && (
        <div className="mt-2 ml-9 space-y-1">
          <p className="text-xs text-gray-500 dark:text-[#71717a] font-mono">{check.details}</p>
          {check.error && (
            <p className="text-xs text-red-500 dark:text-red-400 font-mono">Error: {check.error}</p>
          )}
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
  const checks = run.results?.checks || []
  const grouped = groupChecks(checks)

  const fullySignedOff = !!run.customer_signoff_by && !!run.staff_signoff_by

  return (
    <div className="space-y-6">
      {/* Summary header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">QA Run #{run.id}</h3>
          <p className="text-sm text-gray-500 dark:text-[#71717a]">
            {new Date(run.created_at).toLocaleString()} &middot; {run.run_by} &middot;{' '}
            {run.environment} &middot; {(run.duration_ms / 1000).toFixed(1)}s
          </p>
        </div>
        <div
          className={`rounded-lg px-4 py-2 text-center ${
            run.status === 'passed'
              ? 'bg-green-100 dark:bg-green-900/30'
              : 'bg-red-100 dark:bg-red-900/30'
          }`}
        >
          <p
            className={`text-2xl font-bold ${
              run.status === 'passed'
                ? 'text-green-700 dark:text-green-400'
                : 'text-red-700 dark:text-red-400'
            }`}
          >
            {run.passed_count}/{run.total_count}
          </p>
          <p
            className={`text-xs font-medium ${
              run.status === 'passed'
                ? 'text-green-600 dark:text-green-500'
                : 'text-red-600 dark:text-red-500'
            }`}
          >
            {run.status === 'passed' ? 'ALL PASSED' : 'ISSUES FOUND'}
          </p>
        </div>
      </div>

      {/* Sign-off status */}
      <div className="flex flex-wrap items-center gap-3">
        <SignoffBadge label="Customer" by={run.customer_signoff_by} at={run.customer_signoff_at} />
        <SignoffBadge label="Staff" by={run.staff_signoff_by} at={run.staff_signoff_at} />
        {fullySignedOff && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F59E0B]/10 px-3 py-1 text-xs font-medium text-[#F59E0B]">
            Fully Validated
          </span>
        )}
      </div>

      {/* Sign-off buttons */}
      {user && !fullySignedOff && (
        <div className="flex gap-3">
          {!run.customer_signoff_by && (
            <button
              onClick={() => onSignoff('customer')}
              disabled={signingOff}
              className="rounded-lg bg-[#F59E0B] px-4 py-2 text-sm font-medium text-black hover:bg-[#D97706] disabled:opacity-50"
            >
              {signingOff ? 'Signing...' : 'Sign Off as Customer'}
            </button>
          )}
          {!run.staff_signoff_by && (
            <button
              onClick={() => onSignoff('staff')}
              disabled={signingOff}
              className="rounded-lg border border-[#F59E0B] px-4 py-2 text-sm font-medium text-[#F59E0B] hover:bg-[#F59E0B]/10 disabled:opacity-50"
            >
              {signingOff ? 'Signing...' : 'Sign Off as AI Identity Staff'}
            </button>
          )}
        </div>
      )}

      {/* Check results by section */}
      {SECTIONS.map((section) => {
        const sectionChecks = grouped[section] || []
        if (sectionChecks.length === 0) return null
        const allPassed = sectionChecks.every((c) => c.passed)
        return (
          <div key={section}>
            <div className="mb-2 flex items-center gap-2">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-[#a1a1aa]">{section}</h4>
              <StatusBadge passed={allPassed} />
            </div>
            <div className="space-y-1 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-[#1a1a1d] dark:bg-[#111113]">
              {sectionChecks.map((check) => (
                <CheckRow key={check.step} check={check} />
              ))}
            </div>
          </div>
        )
      })}
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

  async function handleRunQA() {
    setRunning(true)
    setError(null)
    try {
      const run = await triggerQARun()
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
      const updated = await signoffQARun(selectedRun.id, role)
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">QA Checklist</h1>
          <p className="text-sm text-gray-500 dark:text-[#71717a]">
            15-step E2E production validation for design partner onboarding
          </p>
        </div>
        <button
          onClick={handleRunQA}
          disabled={running}
          className="flex items-center gap-2 rounded-lg bg-[#F59E0B] px-5 py-2.5 text-sm font-medium text-black hover:bg-[#D97706] disabled:opacity-50 transition-colors"
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
              Running checks...
            </>
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
              Run QA Checklist
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Run history sidebar */}
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-600 dark:text-[#a1a1aa]">Run History</h2>
          {loading ? (
            <p className="text-sm text-gray-400 dark:text-[#52525b]">Loading...</p>
          ) : runs.length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-[#52525b]">
              No runs yet. Click "Run QA Checklist" to start.
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
                      isSelected
                        ? 'bg-[#F59E0B]/10 ring-1 ring-[#F59E0B]/30'
                        : 'hover:bg-gray-100 dark:hover:bg-[#1a1a1d]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-[#e4e4e7]">
                        Run #{run.id}
                      </span>
                      <span
                        className={`text-xs font-medium ${
                          run.status === 'passed'
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {run.passed_count}/{run.total_count}
                      </span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="text-xs text-gray-400 dark:text-[#52525b]">
                        {new Date(run.created_at).toLocaleDateString()}
                      </span>
                      {fullySignedOff && <span className="text-xs text-[#F59E0B]">Validated</span>}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Run detail */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#1a1a1d] dark:bg-[#0A0A0B]">
          {selectedRun ? (
            <RunDetail run={selectedRun} onSignoff={handleSignoff} signingOff={signingOff} />
          ) : (
            <div className="flex h-64 items-center justify-center text-gray-400 dark:text-[#52525b]">
              <p>Run the QA checklist to see results here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
