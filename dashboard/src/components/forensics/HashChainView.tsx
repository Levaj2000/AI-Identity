/**
 * HashChainView — collapsible visualization of the HMAC integrity chain.
 *
 * Shows each audit entry as a block with truncated hashes, connected
 * by link indicators that turn green (verified) or red (broken).
 */

import { useState } from 'react'
import type { AuditLogEntry } from '../../types/api'

interface Props {
  events: AuditLogEntry[]
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function HashChainView({ events }: Props) {
  const [expanded, setExpanded] = useState(false)

  // Sort entries ascending by id (chain order)
  const sorted = [...events].sort((a, b) => a.id - b.id)

  // Verify consecutive links
  const links: { from: number; to: number; valid: boolean }[] = []
  for (let i = 0; i < sorted.length - 1; i++) {
    links.push({
      from: sorted[i].id,
      to: sorted[i + 1].id,
      valid: sorted[i + 1].prev_hash === sorted[i].entry_hash,
    })
  }

  const brokenCount = links.filter((l) => !l.valid).length
  const allValid = brokenCount === 0

  return (
    <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl overflow-hidden">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-zinc-800/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">🔗</span>
          <span className="text-sm font-medium text-zinc-300">
            Hash Chain ({sorted.length} entries)
          </span>
          {allValid ? (
            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Verified
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              {brokenCount} broken link{brokenCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 text-zinc-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Expanded chain view */}
      {expanded && (
        <div className="px-4 pb-4 max-h-96 overflow-y-auto">
          <div className="space-y-0">
            {sorted.map((entry, idx) => {
              const link = idx < links.length ? links[idx] : null

              return (
                <div key={entry.id}>
                  {/* Entry block */}
                  <div className="bg-zinc-800 rounded-lg px-3 py-2 border border-zinc-700">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs text-zinc-500 shrink-0">#{entry.id}</span>
                        <span className="font-mono text-xs text-zinc-300 truncate">
                          {entry.entry_hash.slice(0, 8)}
                        </span>
                      </div>
                      <span className="text-xs text-zinc-500 shrink-0 whitespace-nowrap">
                        {formatTime(entry.created_at)}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-zinc-600">
                      <span className="font-mono">prev: {entry.prev_hash.slice(0, 8)}</span>
                    </div>
                  </div>

                  {/* Link indicator */}
                  {link && (
                    <div className="flex items-center justify-center py-1">
                      <div className="flex flex-col items-center">
                        <div
                          className={`w-px h-3 ${link.valid ? 'bg-emerald-400' : 'bg-red-400'}`}
                        />
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          className={`h-3 w-3 ${link.valid ? 'text-emerald-400' : 'text-red-400'}`}
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
                            clipRule="evenodd"
                          />
                        </svg>
                        {!link.valid && (
                          <span className="text-xs text-red-400 font-medium">BREAK</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
