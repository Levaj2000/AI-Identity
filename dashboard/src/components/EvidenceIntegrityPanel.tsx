import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { verifyAuditChain } from '../services/api/forensics'
import { useAuth } from '../hooks/useAuth'

interface ChainState {
  valid: boolean
  total_entries: number
  entries_verified: number
  first_broken_id: number | null
  message: string
}

const tabular = { fontVariantNumeric: 'tabular-nums' as const }

/**
 * Evidence & integrity hero — the differentiated trust signal. Wired to the
 * real tamper-evident audit-chain verification (`/api/v1/audit/verify`); no
 * fabricated metrics.
 */
export function EvidenceIntegrityPanel() {
  const { user } = useAuth()
  const [chain, setChain] = useState<ChainState | null | 'error'>(null)

  useEffect(() => {
    if (!user) return
    let cancelled = false
    verifyAuditChain()
      .then((r) => {
        if (!cancelled) setChain(r)
      })
      .catch(() => {
        if (!cancelled) setChain('error')
      })
    return () => {
      cancelled = true
    }
  }, [user])

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-sm font-medium text-ink">Evidence &amp; integrity</h2>
          <p className="text-xs text-subtle">Tamper-evident audit chain · HMAC-SHA256</p>
        </div>
        <Link to="/dashboard/forensics" className="shrink-0 text-xs text-brand hover:underline">
          Open Case File &rarr;
        </Link>
      </div>

      {chain === null && <div className="h-24 animate-pulse rounded-lg bg-elevated" />}

      {chain === 'error' && (
        <p className="text-sm text-subtle">Chain status unavailable right now.</p>
      )}

      {chain && chain !== 'error' && (
        <>
          <div className="flex items-center gap-3">
            <span
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                chain.valid ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'
              }`}
            >
              {chain.valid ? (
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                  <path
                    fillRule="evenodd"
                    d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </span>
            <div>
              <div
                className={`text-base font-medium ${chain.valid ? 'text-success' : 'text-danger'}`}
              >
                {chain.valid ? 'Chain verified' : 'Chain integrity broken'}
              </div>
              <div className="text-xs text-subtle">
                {chain.valid
                  ? 'Gap-free sequence, no entries altered — verifiable offline'
                  : chain.message || `First broken entry: ${chain.first_broken_id ?? 'unknown'}`}
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 border-t border-line pt-4">
            <div>
              <div className="text-xs text-subtle">Entries verified</div>
              <div className="text-lg font-medium text-ink" style={tabular}>
                {chain.entries_verified.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-xs text-subtle">Total entries</div>
              <div className="text-lg font-medium text-ink" style={tabular}>
                {chain.total_entries.toLocaleString()}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
