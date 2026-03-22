/**
 * IncidentReconstructModal — focused incident investigation view.
 *
 * Shows events, active policy, chain verification, and stats
 * for a specific agent + time window.
 */

import { useState } from 'react'
import type { AuditReconstructResponse } from '../../types/api'
import { ForensicsTimeline } from './ForensicsTimeline'

// ── Component ────────────────────────────────────────────────────

interface Props {
  data: AuditReconstructResponse
  onClose: () => void
  onExportJSON: () => void
  onExportCSV: () => void
}

export function IncidentReconstructModal({ data, onClose, onExportJSON, onExportCSV }: Props) {
  const [showPolicy, setShowPolicy] = useState(false)

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-4xl bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-700">
          <div>
            <h2 className="text-lg font-semibold text-zinc-100">Incident Reconstruction</h2>
            <p className="text-sm text-zinc-400 mt-1">
              Agent: <span className="text-amber-400">{data.agent_name || data.agent_id}</span>
              {' | '}
              {new Date(data.start_date).toLocaleDateString()} &ndash;{' '}
              {new Date(data.end_date).toLocaleDateString()}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>

        {/* Chain Verification Banner */}
        <div
          className={`mx-6 mt-4 rounded-lg p-3 text-sm font-medium flex items-center gap-2 ${
            data.chain_verification.valid
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'bg-red-500/10 text-red-400 border border-red-500/20'
          }`}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-5 w-5 shrink-0"
          >
            {data.chain_verification.valid ? (
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                clipRule="evenodd"
              />
            ) : (
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            )}
          </svg>
          <span>
            Chain Integrity: {data.chain_verification.valid ? 'Verified' : 'BROKEN'} &mdash;{' '}
            {data.chain_verification.message}
          </span>
          <span className="ml-auto text-xs text-zinc-500">
            {data.chain_verification.entries_verified} entries verified
          </span>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-6">
          <div className="bg-zinc-800 rounded-lg p-3">
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Events</div>
            <div className="text-xl font-semibold text-zinc-100 mt-1">
              {data.stats.total_events}
            </div>
          </div>
          <div className="bg-zinc-800 rounded-lg p-3">
            <div className="text-xs text-emerald-400 uppercase tracking-wider">Allowed</div>
            <div className="text-xl font-semibold text-emerald-400 mt-1">
              {data.stats.allowed_count}
            </div>
          </div>
          <div className="bg-zinc-800 rounded-lg p-3">
            <div className="text-xs text-red-400 uppercase tracking-wider">Denied</div>
            <div className="text-xl font-semibold text-red-400 mt-1">{data.stats.denied_count}</div>
          </div>
          <div className="bg-zinc-800 rounded-lg p-3">
            <div className="text-xs text-yellow-400 uppercase tracking-wider">Errors</div>
            <div className="text-xl font-semibold text-yellow-400 mt-1">
              {data.stats.error_count}
            </div>
          </div>
        </div>

        {/* Active Policy (collapsible) */}
        {data.active_policy && (
          <div className="mx-6 mb-4">
            <button
              onClick={() => setShowPolicy(!showPolicy)}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className={`h-4 w-4 transition-transform ${showPolicy ? 'rotate-90' : ''}`}
              >
                <path
                  fillRule="evenodd"
                  d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                  clipRule="evenodd"
                />
              </svg>
              Active Policy (v{data.active_policy.version})
            </button>
            {showPolicy && (
              <pre className="mt-2 p-3 bg-zinc-800 rounded-lg text-xs text-zinc-300 overflow-x-auto border border-zinc-700">
                {JSON.stringify(data.active_policy.rules, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Event Timeline */}
        <div className="px-6 pb-4 max-h-96 overflow-y-auto">
          <h3 className="text-sm font-medium text-zinc-300 mb-3">
            Event Timeline ({data.events.length} events)
          </h3>
          <ForensicsTimeline events={data.events} />
        </div>

        {/* Footer with export buttons */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-zinc-700">
          <button
            onClick={onExportCSV}
            className="px-4 py-2 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-600"
          >
            Export CSV
          </button>
          <button
            onClick={onExportJSON}
            className="px-4 py-2 text-sm font-medium text-zinc-100 bg-amber-600 hover:bg-amber-500 rounded-lg transition-colors"
          >
            Export JSON Report
          </button>
        </div>
      </div>
    </div>
  )
}
