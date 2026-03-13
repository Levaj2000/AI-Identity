import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from '../components/Sidebar'
import { HealthIndicator } from '../components/HealthIndicator'
import { useHealthCheck } from '../hooks/useHealthCheck'

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const health = useHealthCheck()

  return (
    <div className="flex h-screen bg-gray-50 font-[Inter,system-ui,sans-serif] text-gray-900 dark:bg-slate-950 dark:text-slate-100">
      {/* Sidebar */}
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar (mobile hamburger + health indicator) */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-950 lg:px-6">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-800 lg:hidden"
            aria-label="Open sidebar"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path
                fillRule="evenodd"
                d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z"
                clipRule="evenodd"
              />
            </svg>
          </button>

          {/* Brand visible on mobile (hidden on desktop since sidebar shows it) */}
          <h1 className="text-lg font-bold tracking-tight lg:hidden">
            <span className="text-indigo-500">AI</span>{' '}
            <span className="text-gray-900 dark:text-slate-100">Identity</span>
          </h1>

          {/* Health indicator — pushed to the right */}
          <div className="ml-auto">
            <HealthIndicator isHealthy={health.isHealthy} version={health.version} />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
