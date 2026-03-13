import { ENDPOINTS } from '../../config/api'

interface AgentEmptyStateProps {
  hasFilters: boolean
  onClearFilters: () => void
}

export function AgentEmptyState({ hasFilters, onClearFilters }: AgentEmptyStateProps) {
  if (hasFilters) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white py-16 text-center dark:border-slate-800 dark:bg-slate-900">
        {/* Search icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="mx-auto mb-4 h-10 w-10 text-gray-300 dark:text-slate-600"
        >
          <path
            fillRule="evenodd"
            d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
            clipRule="evenodd"
          />
        </svg>
        <h3 className="mb-1 text-lg font-semibold text-gray-900 dark:text-slate-100">
          No matching agents
        </h3>
        <p className="mb-6 text-sm text-gray-500 dark:text-slate-400">
          Try adjusting your filters to find what you&rsquo;re looking for.
        </p>
        <button
          onClick={onClearFilters}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Clear filters
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 py-16 text-center dark:border-indigo-500/20 dark:bg-slate-900/50">
      {/* Agent/people icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="mx-auto mb-4 h-10 w-10 text-indigo-400 dark:text-indigo-500"
      >
        <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
      </svg>
      <h3 className="mb-1 text-lg font-semibold text-gray-900 dark:text-slate-100">
        No agents yet
      </h3>
      <p className="mb-6 text-sm text-gray-500 dark:text-slate-400">
        Create your first agent via the API to get started.
      </p>
      <a
        href={ENDPOINTS.DOCS}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-500"
      >
        API Documentation
        <span aria-hidden="true">&rarr;</span>
      </a>
    </div>
  )
}
