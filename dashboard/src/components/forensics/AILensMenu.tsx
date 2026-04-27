/**
 * AILensMenu — split button exposing AI summary "lenses".
 *
 * Primary action runs the broad "Explain N visible events" summary.
 * The chevron opens a menu of focused lenses that send a tailored
 * focus_hint and pre-scoped event set to /audit/summarize.
 */

import { useEffect, useRef, useState } from 'react'

export type AILens = 'explain_visible' | 'explain_denials' | 'spot_anomalies' | 'reconstruct_actors'

interface LensOption {
  id: AILens
  icon: string
  label: string
  description: string
  /** Optional disabled reason — the button is still rendered so users see the lens exists. */
  disabledReason?: string
}

interface Props {
  visibleCount: number
  /** Whether any visible event is a denial. Disables "Explain denials" if false. */
  hasDenials: boolean
  /** Whether any visible event has an anomaly. Disables "Spot anomalies" if false. */
  hasAnomalies: boolean
  loading: boolean
  onSelect: (lens: AILens) => void
}

export function AILensMenu({ visibleCount, hasDenials, hasAnomalies, loading, onSelect }: Props) {
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // Close on outside click or Escape
  useEffect(() => {
    if (!open) return
    function onDocClick(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const lenses: LensOption[] = [
    {
      id: 'explain_denials',
      icon: '🚨',
      label: 'Why were requests denied?',
      description: 'Group denials by deny_reason and recommend fixes',
      disabledReason: hasDenials ? undefined : 'No denials in this view',
    },
    {
      id: 'spot_anomalies',
      icon: '📊',
      label: 'Spot anomalies in this window',
      description: 'Explain deny clusters, latency spikes, and cost outliers',
      disabledReason: hasAnomalies ? undefined : 'No anomalies detected',
    },
    {
      id: 'reconstruct_actors',
      icon: '🕐',
      label: 'Reconstruct who did what',
      description: 'Build an actor-ordered narrative of operations',
    },
  ]

  const select = (lens: AILens) => {
    setOpen(false)
    onSelect(lens)
  }

  return (
    <div ref={wrapperRef} className="relative">
      <div className="inline-flex rounded-lg overflow-hidden border border-purple-400/40">
        {/* Primary: Explain N visible events */}
        <button
          onClick={() => select('explain_visible')}
          disabled={loading || visibleCount === 0}
          title={`Analyze the ${visibleCount} event${visibleCount === 1 ? '' : 's'} matching your current filters`}
          className="px-3 py-2 text-sm font-medium text-zinc-100 bg-purple-500/90 hover:bg-purple-400/90 transition-colors inline-flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <div className="h-3.5 w-3.5 border-2 border-zinc-200 border-t-transparent rounded-full animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-3.5 w-3.5"
              >
                <path d="M15.98 1.804a1 1 0 00-1.96 0l-.24 1.192a1 1 0 01-.784.785l-1.192.238a1 1 0 000 1.962l1.192.238a1 1 0 01.785.785l.238 1.192a1 1 0 001.962 0l.238-1.192a1 1 0 01.785-.785l1.192-.238a1 1 0 000-1.962l-1.192-.238a1 1 0 01-.785-.785l-.238-1.192zM6.949 5.684a1 1 0 00-1.898 0l-.683 2.051a1 1 0 01-.633.633l-2.051.683a1 1 0 000 1.898l2.051.684a1 1 0 01.633.632l.683 2.051a1 1 0 001.898 0l.683-2.051a1 1 0 01.633-.633l2.051-.683a1 1 0 000-1.898l-2.051-.683a1 1 0 01-.633-.633L6.95 5.684z" />
              </svg>
              Explain {visibleCount} visible event{visibleCount === 1 ? '' : 's'}
            </>
          )}
        </button>

        {/* Chevron — opens lens menu */}
        <button
          onClick={() => setOpen((v) => !v)}
          disabled={loading || visibleCount === 0}
          aria-haspopup="menu"
          aria-expanded={open}
          title="Choose a focused AI lens"
          className="px-2 py-2 text-zinc-100 bg-purple-500/90 hover:bg-purple-400/90 transition-colors border-l border-purple-300/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`}
          >
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {/* Dropdown menu */}
      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-80 rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl z-30 overflow-hidden"
        >
          <div className="px-3 py-2 border-b border-zinc-800 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            Focused AI Lenses
          </div>
          {lenses.map((lens) => {
            const disabled = !!lens.disabledReason
            return (
              <button
                key={lens.id}
                role="menuitem"
                onClick={() => !disabled && select(lens.id)}
                disabled={disabled}
                title={lens.disabledReason}
                className={`w-full text-left px-3 py-2.5 flex items-start gap-3 transition-colors border-b border-zinc-800 last:border-b-0 ${
                  disabled
                    ? 'opacity-40 cursor-not-allowed'
                    : 'hover:bg-purple-500/10 cursor-pointer'
                }`}
              >
                <span className="text-lg leading-6 shrink-0">{lens.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-zinc-100">{lens.label}</div>
                  <div className="text-xs text-zinc-500 mt-0.5">
                    {lens.disabledReason || lens.description}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
