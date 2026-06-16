/**
 * FilterSummaryBar — always-visible readout of the current forensics filter
 * state.
 *
 * The active date window is *always* shown (not just when narrowed), which is
 * the core fix for the empty-screen-on-bad-date confusion: the analyst can
 * always see exactly which window the table reflects. Non-default filters
 * (agent, decision, endpoint, etc.) render as removable chips so a drill-down
 * is reversible in one click.
 */

export interface FilterChip {
  key: string
  label: string
  onClear: () => void
}

interface Props {
  total: number
  windowLabel: string
  chips: FilterChip[]
  onClearAll: () => void
}

export function FilterSummaryBar({ total, windowLabel, chips, onClearAll }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-line bg-surface px-4 py-3">
      <p className="text-sm text-muted">
        Showing <span className="font-semibold text-ink">{total.toLocaleString()}</span> event
        {total !== 1 ? 's' : ''} · <span className="text-ink">{windowLabel}</span>
      </p>

      {chips.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {chips.map((chip) => (
            <span
              key={chip.key}
              className="inline-flex items-center gap-1.5 rounded-full border border-line bg-elevated px-2.5 py-0.5 text-xs text-muted"
            >
              {chip.label}
              <button
                onClick={chip.onClear}
                title={`Clear ${chip.key} filter`}
                aria-label={`Clear ${chip.key} filter`}
                className="text-subtle hover:text-ink transition-colors"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-3 w-3"
                >
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </span>
          ))}
          <button
            onClick={onClearAll}
            className="text-xs text-subtle hover:text-ink transition-colors underline-offset-2 hover:underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  )
}
