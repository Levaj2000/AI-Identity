interface PaginationProps {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
}

/** Builds an array of page numbers + ellipsis markers for display. */
function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const pages: (number | '...')[] = [1]

  if (current > 3) pages.push('...')

  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (current < total - 2) pages.push('...')

  pages.push(total)
  return pages
}

export function Pagination({ page, totalPages, total, pageSize, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null

  const pages = getPageNumbers(page, totalPages)
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
      {/* Result summary */}
      <p className="text-sm text-subtle">
        Showing{' '}
        <span className="font-[JetBrains_Mono,monospace] font-medium text-ink">
          {from}-{to}
        </span>{' '}
        of <span className="font-[JetBrains_Mono,monospace] font-medium text-ink">{total}</span>{' '}
        agents
      </p>

      {/* Page buttons */}
      <nav className="flex items-center gap-1" aria-label="Pagination">
        {/* Previous */}
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Previous page"
        >
          &larr;
        </button>

        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`ellipsis-${i}`} className="px-2 py-2 text-sm text-faint">
              &hellip;
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              disabled={p === page}
              aria-current={p === page ? 'page' : undefined}
              aria-label={`Go to page ${p}`}
              className={`min-w-[2.25rem] rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                p === page ? 'bg-brand text-brand-ink' : 'text-muted hover:bg-elevated'
              }`}
            >
              {p}
            </button>
          ),
        )}

        {/* Next */}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Next page"
        >
          &rarr;
        </button>
      </nav>
    </div>
  )
}
