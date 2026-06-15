/* eslint-disable react-refresh/only-export-components -- data/config module, not a component file */
import type { ReactNode } from 'react'

export interface NavItem {
  label: string
  to: string
  end?: boolean
  adminOnly?: boolean
  icon: ReactNode
}

export interface NavGroup {
  /** Section heading shown in the rail; omitted for the top (Overview) group. */
  title?: string
  items: NavItem[]
}

/* ── Icons (20×20, currentColor) ─────────────────────────────────── */
const svg = (children: ReactNode) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    className="h-5 w-5"
  >
    {children}
  </svg>
)

const icons = {
  overview: svg(
    <path
      fillRule="evenodd"
      d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 11h-1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H9a1 1 0 00-1 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-6H3a1 1 0 01-.707-1.707l7-7z"
      clipRule="evenodd"
    />,
  ),
  agents: svg(
    <path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />,
  ),
  organization: svg(
    <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />,
  ),
  approvals: svg(
    <path
      fillRule="evenodd"
      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
      clipRule="evenodd"
    />,
  ),
  caseFile: svg(
    <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" />,
  ),
  compliance: svg(
    <path
      fillRule="evenodd"
      d="M9.661 2.237a.531.531 0 01.678 0 11.947 11.947 0 007.078 2.749.5.5 0 01.479.425c.069.52.104 1.05.104 1.59 0 5.162-3.26 9.563-7.834 11.256a.48.48 0 01-.332 0C5.26 16.564 2 12.163 2 7c0-.538.035-1.069.104-1.589a.5.5 0 01.48-.425 11.947 11.947 0 007.077-2.75zm4.196 5.954a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
      clipRule="evenodd"
    />,
  ),
  qa: svg(
    <path
      fillRule="evenodd"
      d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
      clipRule="evenodd"
    />,
  ),
  shadow: svg(
    <>
      <path
        fillRule="evenodd"
        d="M3.28 2.22a.75.75 0 00-1.06 1.06l14.5 14.5a.75.75 0 101.06-1.06l-1.745-1.745a10.029 10.029 0 003.3-4.38 1.651 1.651 0 000-1.185A10.004 10.004 0 009.999 3a9.956 9.956 0 00-4.744 1.194L3.28 2.22zM7.752 6.69l1.092 1.092a2.5 2.5 0 013.374 3.373l1.092 1.092a4 4 0 00-5.558-5.558z"
        clipRule="evenodd"
      />
      <path d="M10.748 13.93l2.523 2.523a9.987 9.987 0 01-3.27.547c-4.258 0-7.894-2.66-9.337-6.41a1.651 1.651 0 010-1.186A10.007 10.007 0 012.839 6.02L6.07 9.252a4 4 0 004.678 4.678z" />
    </>,
  ),
  usage: svg(
    <path d="M1 4.75C1 3.784 1.784 3 2.75 3h14.5c.966 0 1.75.784 1.75 1.75v10.515a1.75 1.75 0 01-1.75 1.75h-1.5c-.078 0-.155-.005-.23-.015H4.48c-.075.01-.152.015-.23.015h-1.5A1.75 1.75 0 011 15.265V4.75zm3.5 0a.75.75 0 00-.75.75v9.5c0 .414.336.75.75.75h11a.75.75 0 00.75-.75v-9.5a.75.75 0 00-.75-.75h-11z" />,
  ),
  demo: svg(
    <path
      fillRule="evenodd"
      d="M2 4.25A2.25 2.25 0 014.25 2h11.5A2.25 2.25 0 0118 4.25v8.5A2.25 2.25 0 0115.75 15h-3.105a3.501 3.501 0 001.1 1.677A.75.75 0 0113.26 18H6.74a.75.75 0 01-.484-1.323A3.501 3.501 0 007.355 15H4.25A2.25 2.25 0 012 12.75v-8.5zm1.5 0a.75.75 0 01.75-.75h11.5a.75.75 0 01.75.75v7.5a.75.75 0 01-.75.75H4.25a.75.75 0 01-.75-.75v-7.5z"
      clipRule="evenodd"
    />,
  ),
  support: svg(
    <path
      fillRule="evenodd"
      d="M10 2a6 6 0 00-6 6c0 1.887-.454 3.665-1.257 5.234a.75.75 0 00.515 1.076 32.91 32.91 0 003.256.508 3.5 3.5 0 006.972 0 32.903 32.903 0 003.256-.508.75.75 0 00.515-1.076A11.448 11.448 0 0116 8a6 6 0 00-6-6zM8.05 14.943a33.54 33.54 0 003.9 0 2 2 0 01-3.9 0z"
      clipRule="evenodd"
    />,
  ),
  properties: svg(
    <path d="M4.632 3.533A2 2 0 016.577 2h6.846a2 2 0 011.945 1.533l1.976 8.234A3.489 3.489 0 0016 11.5H4c-.476 0-.93.095-1.344.267l1.976-8.234zM4 13a2 2 0 100 4h12a2 2 0 100-4H4z" />,
  ),
  admin: svg(
    <path
      fillRule="evenodd"
      d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
      clipRule="evenodd"
    />,
  ),
}

/**
 * Grouped navigation — the enterprise IA. Only routes that exist today are
 * listed; new flagship surfaces (Attestation, OCSF interop) get added here
 * when their pages ship.
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    items: [{ label: 'Overview', to: '/dashboard', end: true, icon: icons.overview }],
  },
  {
    title: 'Identity',
    items: [
      { label: 'Agents', to: '/dashboard/agents', icon: icons.agents },
      { label: 'Organization', to: '/dashboard/organization', icon: icons.organization },
    ],
  },
  {
    title: 'Control',
    items: [{ label: 'Approvals', to: '/dashboard/approvals', icon: icons.approvals }],
  },
  {
    title: 'Assurance',
    items: [
      { label: 'Case File', to: '/dashboard/forensics', icon: icons.caseFile },
      { label: 'Compliance', to: '/dashboard/compliance', icon: icons.compliance },
      { label: 'Onboarding QA', to: '/dashboard/qa', icon: icons.qa },
    ],
  },
  {
    title: 'Detect',
    items: [{ label: 'Shadow agents', to: '/dashboard/shadow-agents', icon: icons.shadow }],
  },
  {
    title: 'Account',
    items: [
      { label: 'Usage & billing', to: '/dashboard/usage', icon: icons.usage },
      { label: 'Demo', to: '/demo', end: true, icon: icons.demo },
      { label: 'Support', to: '/dashboard/support', icon: icons.support },
      {
        label: 'Web properties',
        to: '/dashboard/properties',
        adminOnly: true,
        icon: icons.properties,
      },
      { label: 'Admin', to: '/dashboard/admin', adminOnly: true, icon: icons.admin },
    ],
  },
]

/** Flat lookup of all nav items (for breadcrumb/title resolution). */
export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items)
