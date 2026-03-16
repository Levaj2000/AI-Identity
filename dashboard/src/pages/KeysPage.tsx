import { Link } from 'react-router-dom'

export function KeysPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">Keys</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-[#a1a1aa]">
          View and manage API keys across all agents.
        </p>
      </div>

      {/* Placeholder content */}
      <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-12 text-center dark:border-[#2a2a2d] dark:bg-[#111113]/50">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="mx-auto h-10 w-10 text-gray-400 dark:text-[#52525b]"
        >
          <path
            fillRule="evenodd"
            d="M8 7a5 5 0 113.61 4.804l-1.903 1.903A.75.75 0 019.17 14H8v1.17a.75.75 0 01-.22.53l-.5.5a.75.75 0 01-.531.22H5.672a.75.75 0 01-.53-.22l-.5-.5a.75.75 0 01-.22-.53V13.59a.75.75 0 01.22-.53L8.196 9.54A5.003 5.003 0 018 7zm5-3a.75.75 0 000 1.5A1.5 1.5 0 0114.5 7 .75.75 0 0016 7a3 3 0 00-3-3z"
            clipRule="evenodd"
          />
        </svg>
        <h2 className="mt-4 text-lg font-semibold text-gray-700 dark:text-[#d4d4d8]">
          All API Keys
        </h2>
        <p className="mt-2 text-sm text-gray-500 dark:text-[#71717a]">
          A global view of all API keys will appear here. For now, manage keys from individual agent
          pages.
        </p>
        <Link
          to="/dashboard/agents"
          className="mt-6 inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#d4d4d8] dark:hover:bg-[#2a2a2d]"
        >
          View Agents
          <span aria-hidden="true">&rarr;</span>
        </Link>
      </div>
    </div>
  )
}
