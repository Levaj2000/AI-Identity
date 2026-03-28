import { ENDPOINTS } from '../../config/api'

interface AgentEmptyStateProps {
  hasFilters: boolean
  onClearFilters: () => void
}

export function AgentEmptyState({ hasFilters, onClearFilters }: AgentEmptyStateProps) {
  if (hasFilters) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white py-16 text-center dark:border-[#1a1a1d] dark:bg-[#10131C]">
        {/* Search icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="mx-auto mb-4 h-10 w-10 text-gray-300 dark:text-[#52525b]"
        >
          <path
            fillRule="evenodd"
            d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
            clipRule="evenodd"
          />
        </svg>
        <h3 className="mb-1 text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
          No matching agents
        </h3>
        <p className="mb-6 text-sm text-gray-500 dark:text-[#a1a1aa]">
          Try adjusting your filters to find what you&rsquo;re looking for.
        </p>
        <button
          onClick={onClearFilters}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#e4e4e7] dark:hover:bg-[#2a2a2d]"
        >
          Clear filters
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[#A6DAFF]/20 bg-[#A6DAFF]/5 py-16 text-center dark:border-[#A6DAFF]/20 dark:bg-[#10131C]/50">
      {/* Agent/people icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="mx-auto mb-4 h-10 w-10 text-[#A6DAFF] dark:text-[#A6DAFF]"
      >
        <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
      </svg>
      <h3 className="mb-1 text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
        No agents yet
      </h3>
      <p className="mb-6 text-sm text-gray-500 dark:text-[#a1a1aa]">
        Create your first agent to get started with identity, policy, compliance, and forensics.
      </p>
      <div className="flex items-center justify-center gap-3">
        <a
          href="/dashboard/agents/new"
          className="inline-flex items-center gap-2 rounded-lg bg-[#A6DAFF] px-6 py-3 text-sm font-semibold text-[#04070D] transition-colors hover:bg-[#A6DAFF]/80"
        >
          Create Agent
          <span aria-hidden="true">&rarr;</span>
        </a>
        <a
          href={ENDPOINTS.DOCS}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#e4e4e7] dark:hover:bg-[#2a2a2d]"
        >
          API Docs
        </a>
      </div>
    </div>
  )
}
