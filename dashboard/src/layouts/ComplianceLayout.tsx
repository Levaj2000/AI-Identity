import { NavLink, Outlet } from 'react-router-dom'

/**
 * Tab container for the Compliance section.
 *
 * Renders the "Audit Log" ↔ "Framework Exports" tab bar above an
 * <Outlet />. Child routes (CompliancePage / ComplianceExportsPage)
 * mount into the outlet. The tabs themselves are NavLinks so deep
 * links (e.g. /dashboard/compliance/exports) still work and the
 * highlight state stays in sync with the URL.
 *
 * Why: the raw audit_log dump on the first tab and the signed
 * framework-scoped ZIP on the second are different products for
 * different consumers (on-call vs auditor), but they live close
 * enough together in the IA that a single nav entry with tabs
 * beats two separate sidebar items. Same pattern as Drata / Vanta.
 */
export function ComplianceLayout() {
  return (
    <div className="space-y-6">
      <div
        role="tablist"
        aria-label="Compliance sections"
        className="flex items-center gap-1 border-b border-gray-200 dark:border-[#1a1a1d]"
      >
        <ComplianceTab to="/dashboard/compliance" label="Audit Log" end />
        <ComplianceTab to="/dashboard/compliance/exports" label="Framework Exports" />
      </div>
      <Outlet />
    </div>
  )
}

interface ComplianceTabProps {
  to: string
  label: string
  end?: boolean
}

function ComplianceTab({ to, label, end }: ComplianceTabProps) {
  // end={true} on the audit-log tab so it doesn't match when we're on
  // the nested /exports path. Matches the same NavLink discipline the
  // sidebar uses for parent routes with children.
  return (
    <NavLink
      to={to}
      end={end}
      role="tab"
      className={({ isActive }) =>
        [
          'relative -mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'border-[#A6DAFF] text-gray-900 dark:text-[#e4e4e7]'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-[#71717a] dark:hover:text-[#d4d4d8]',
        ].join(' ')
      }
    >
      {label}
    </NavLink>
  )
}
