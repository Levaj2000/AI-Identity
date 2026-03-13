import { Link } from 'react-router-dom'
import { useDashboardData } from '../hooks/useDashboardData'
import { relativeTime } from '../lib/time'

const statusStyles: Record<string, string> = {
  active:
    'border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
  suspended:
    'border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
  revoked: 'border-red-500/30 bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400',
}

export function AgentsPage() {
  const { recentAgents, isLoading, error } = useDashboardData()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Agents</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
            Manage your AI agent identities and permissions.
          </p>
        </div>
        <button
          disabled
          className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg bg-indigo-600/50 px-4 py-2 text-sm font-semibold text-white/60"
          title="Coming soon"
        >
          New Agent
          <span className="rounded-full bg-indigo-500/30 px-2 py-0.5 text-xs">Soon</span>
        </button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-gray-200 dark:bg-slate-900" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-6 dark:border-red-500/20 dark:bg-red-500/10">
          <p className="text-sm text-red-600 dark:text-red-400">{error.message}</p>
        </div>
      )}

      {!isLoading && !error && recentAgents.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="mx-auto h-10 w-10 text-gray-400 dark:text-slate-600"
          >
            <path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
          </svg>
          <h3 className="mt-4 font-semibold text-gray-700 dark:text-slate-300">No agents yet</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-slate-500">
            Create your first agent via the API to get started.
          </p>
        </div>
      )}

      {!isLoading && !error && recentAgents.length > 0 && (
        <div className="space-y-3">
          {recentAgents.map((agent) => (
            <Link
              key={agent.id}
              to={`/agents/${agent.id}`}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700 dark:hover:bg-slate-800"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-gray-900 dark:text-slate-100">
                  {agent.name}
                </p>
                {agent.description && (
                  <p className="truncate text-sm text-gray-500 dark:text-slate-500">
                    {agent.description}
                  </p>
                )}
              </div>
              <div className="ml-4 flex shrink-0 items-center gap-3">
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyles[agent.status] ?? ''}`}
                >
                  {agent.status}
                </span>
                <span className="text-xs text-gray-400 dark:text-slate-600">
                  {relativeTime(agent.updated_at)}
                </span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4 text-gray-400 dark:text-slate-600"
                >
                  <path
                    fillRule="evenodd"
                    d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
