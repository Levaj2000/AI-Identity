import { ENDPOINTS } from '../../config/api'

interface AgentEmptyStateProps {
  hasFilters: boolean
  onClearFilters: () => void
}

export function AgentEmptyState({ hasFilters, onClearFilters }: AgentEmptyStateProps) {
  if (hasFilters) {
    return (
      <div className="rounded-xl border border-line bg-surface py-16 text-center">
        {/* Search icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="mx-auto mb-4 h-10 w-10 text-faint"
        >
          <path
            fillRule="evenodd"
            d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
            clipRule="evenodd"
          />
        </svg>
        <h3 className="mb-1 text-lg font-semibold text-ink">No matching agents</h3>
        <p className="mb-6 text-sm text-subtle">
          Try adjusting your filters to find what you&rsquo;re looking for.
        </p>
        <button
          onClick={onClearFilters}
          className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-elevated"
        >
          Clear filters
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-brand bg-brand-soft py-16 text-center">
      {/* Agent/people icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="mx-auto mb-4 h-10 w-10 text-brand"
      >
        <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
      </svg>
      <h3 className="mb-1 text-lg font-semibold text-ink">No agents yet</h3>
      <p className="mb-6 text-sm text-subtle">
        Create your first agent to get started with identity, policy, compliance, and forensics.
      </p>
      <div className="flex items-center justify-center gap-3">
        <a
          href="/dashboard/agents/new"
          className="inline-flex items-center gap-2 rounded-lg bg-brand px-6 py-3 text-sm font-semibold text-brand-ink transition-colors hover:bg-brand-hover"
        >
          Create Agent
          <span aria-hidden="true">&rarr;</span>
        </a>
        <a
          href={ENDPOINTS.DOCS}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-6 py-3 text-sm font-semibold text-ink transition-colors hover:bg-elevated"
        >
          API Docs
        </a>
      </div>
    </div>
  )
}
