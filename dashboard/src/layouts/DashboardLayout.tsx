import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '../components/Sidebar'
import { HealthIndicator } from '../components/HealthIndicator'
import { useHealthCheck } from '../hooks/useHealthCheck'
import { NAV_ITEMS } from '../config/nav'

/** Resolve the current page's label from the nav config (longest path match). */
function useCurrentTitle(): string {
  const { pathname } = useLocation()
  let best = ''
  let title = 'Dashboard'
  for (const item of NAV_ITEMS) {
    const match = item.end
      ? pathname === item.to
      : pathname === item.to || pathname.startsWith(item.to + '/')
    if (match && item.to.length > best.length) {
      best = item.to
      title = item.label
    }
  }
  return title
}

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const health = useHealthCheck()
  const title = useCurrentTitle()

  return (
    <div className="relative flex h-screen bg-canvas font-[Inter,system-ui,sans-serif] text-ink">
      {/* Navy nav rail */}
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar — clinical: white surface, breadcrumb, status */}
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-line bg-surface px-4 lg:px-6">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-2 text-muted hover:bg-elevated lg:hidden"
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

          {/* Breadcrumb / page title */}
          <div className="flex min-w-0 items-center gap-2">
            <span className="hidden text-sm text-subtle sm:inline">AI Identity</span>
            <span className="hidden text-subtle sm:inline" aria-hidden="true">
              /
            </span>
            <span className="truncate text-sm font-medium text-ink">{title}</span>
          </div>

          {/* Status — pushed right */}
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
