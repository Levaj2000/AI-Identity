import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useClerk } from '@clerk/react'
import { ThemeToggle } from './ThemeToggle'
import { AIIdentityLogo5 } from '../components/AIIdentityLogo'
import { useAuth } from '../hooks/useAuth'
import { getQAHasPending } from '../services/api/qa'
import { NAV_GROUPS } from '../config/nav'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user } = useAuth()
  const { signOut } = useClerk()
  const navigate = useNavigate()

  // QA pending indicator
  const [qaPending, setQaPending] = useState(false)
  useEffect(() => {
    getQAHasPending()
      .then((r) => setQaPending(r.has_pending))
      .catch(() => {})
  }, [])

  function handleLogout() {
    signOut(() => navigate('/login'))
  }

  const isAdmin = user?.role === 'admin'

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Navy nav rail — constant dark in both themes (brand anchor) */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-rail-line bg-rail text-rail-fg transition-transform duration-200 ease-in-out lg:static lg:z-auto lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand */}
        <div className="flex h-16 shrink-0 items-center gap-2 border-b border-rail-line px-6">
          <AIIdentityLogo5 className="h-[28px] w-auto" variant="primary" />
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
          {NAV_GROUPS.map((group, gi) => {
            const items = group.items.filter((i) => !i.adminOnly || isAdmin)
            if (items.length === 0) return null
            return (
              <div key={group.title ?? `g${gi}`} className="space-y-1">
                {group.title && (
                  <p className="px-3 pb-1 text-[10px] font-medium uppercase tracking-[0.1em] text-rail-section">
                    {group.title}
                  </p>
                )}
                {items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                        isActive
                          ? 'bg-rail-active font-medium text-rail-active-fg'
                          : 'text-rail-muted hover:bg-rail-active/60 hover:text-rail-fg'
                      }`
                    }
                  >
                    {item.icon}
                    {item.label}
                    {item.to === '/dashboard/qa' && qaPending && (
                      <span className="ml-auto h-2 w-2 rounded-full bg-danger" />
                    )}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>

        {/* Footer — user info + logout */}
        <div className="border-t border-rail-line px-4 py-4">
          {user && (
            <div className="mb-3 flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-rail-fg">{user.email}</p>
                <p className="text-xs text-rail-muted">
                  {user.role} &middot; {user.tier}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="ml-2 rounded-md p-2 text-rail-muted hover:bg-rail-active/60 hover:text-rail-fg"
                title="Log out"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z"
                    clipRule="evenodd"
                  />
                  <path
                    fillRule="evenodd"
                    d="M19 10a.75.75 0 00-.75-.75H8.704l1.048-.943a.75.75 0 10-1.004-1.114l-2.5 2.25a.75.75 0 000 1.114l2.5 2.25a.75.75 0 101.004-1.114l-1.048-.943h9.546A.75.75 0 0019 10z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          )}
          <div className="flex items-center justify-between">
            <p className="text-xs text-rail-muted">&copy; {new Date().getFullYear()} AI Identity</p>
            <ThemeToggle />
          </div>
        </div>
      </aside>
    </>
  )
}
