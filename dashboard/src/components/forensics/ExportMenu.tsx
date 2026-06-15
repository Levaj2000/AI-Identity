import { useState } from 'react'

export interface ExportItem {
  label: string
  hint?: string
  onClick: () => void
}

/** A compact "Export ▾" dropdown that groups the Case File export formats. */
export function ExportMenu({ items }: { items: ExportItem[] }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-lg border border-line-strong bg-elevated px-3 py-2 text-sm font-medium text-muted transition-colors hover:text-ink"
      >
        Export
        <span aria-hidden="true" className="text-xs">
          ▾
        </span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden="true" />
          <div
            role="menu"
            className="absolute right-0 z-20 mt-1 w-60 overflow-hidden rounded-lg border border-line bg-surface py-1 shadow-lg"
          >
            {items.map((it) => (
              <button
                key={it.label}
                role="menuitem"
                onClick={() => {
                  setOpen(false)
                  it.onClick()
                }}
                className="block w-full px-3 py-2 text-left transition-colors hover:bg-elevated"
              >
                <span className="block text-sm text-ink">{it.label}</span>
                {it.hint && <span className="block text-xs text-subtle">{it.hint}</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
