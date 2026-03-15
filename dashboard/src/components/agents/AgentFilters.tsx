import type { AgentStatus } from '../../types/api'

interface AgentFiltersProps {
  status: AgentStatus | undefined
  onStatusChange: (status: AgentStatus | undefined) => void
  capability: string
  onCapabilityChange: (capability: string) => void
}

export function AgentFilters({
  status,
  onStatusChange,
  capability,
  onCapabilityChange,
}: AgentFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      {/* Status dropdown */}
      <select
        value={status || ''}
        onChange={(e) => onStatusChange((e.target.value as AgentStatus) || undefined)}
        aria-label="Filter by status"
        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 transition-colors focus:border-[#00FFC2] focus:outline-none focus:ring-2 focus:ring-[#00FFC2]/50 sm:w-44 dark:border-[#2a2a2d] dark:bg-[#111113] dark:text-[#e4e4e7]"
      >
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="suspended">Suspended</option>
        <option value="revoked">Revoked</option>
      </select>

      {/* Capability search */}
      <div className="relative flex-1">
        {/* Search icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-[#71717a]"
        >
          <path
            fillRule="evenodd"
            d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
            clipRule="evenodd"
          />
        </svg>
        <input
          type="text"
          value={capability}
          onChange={(e) => onCapabilityChange(e.target.value)}
          placeholder="Filter by capability..."
          aria-label="Filter by capability"
          className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm text-gray-700 transition-colors focus:border-[#00FFC2] focus:outline-none focus:ring-2 focus:ring-[#00FFC2]/50 dark:border-[#2a2a2d] dark:bg-[#111113] dark:text-[#e4e4e7] dark:placeholder-[#71717a]"
        />
      </div>
    </div>
  )
}
