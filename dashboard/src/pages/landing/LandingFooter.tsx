import { Logo } from '../../components/Logo'

const footerLinks = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'API Docs', href: 'https://api.ai-identity.co/docs' },
    { label: 'Dashboard', href: '/app' },
  ],
  Company: [
    { label: 'About', href: 'https://ai-identity.co' },
    { label: 'Blog', href: 'https://ai-identity.co' },
    {
      label: 'Design Partners',
      href: 'mailto:jeff@ai-identity.co?subject=Design%20Partner%20Interest',
    },
    { label: 'Contact', href: 'mailto:jeff@ai-identity.co' },
  ],
  Developers: [
    { label: 'Quickstart', href: 'https://api.ai-identity.co/docs' },
    { label: 'API Reference', href: 'https://api.ai-identity.co/redoc' },
    { label: 'GitHub', href: 'https://github.com/Levaj2000/AI-Identity' },
    { label: 'Status', href: 'https://api.ai-identity.co/health' },
  ],
}

export function LandingFooter() {
  return (
    <footer className="border-t border-gray-200 bg-white px-6 py-12 dark:border-slate-800 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {/* Logo + tagline */}
          <div>
            <Logo variant="full" size={28} />
            <p className="mt-4 text-sm leading-relaxed text-gray-500 dark:text-slate-400">
              Identity, keys, and audit for AI agents. Built for teams shipping autonomous systems.
            </p>
          </div>

          {/* Link groups */}
          {Object.entries(footerLinks).map(([group, links]) => (
            <div key={group}>
              <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-slate-200">
                {group}
              </h4>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-gray-500 transition-colors hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400"
                      {...(link.href.startsWith('http')
                        ? { target: '_blank', rel: 'noopener noreferrer' }
                        : {})}
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-gray-200 pt-8 dark:border-slate-800 sm:flex-row">
          <p className="text-xs text-gray-400 dark:text-slate-500">
            &copy; {new Date().getFullYear()} AI Identity. All rights reserved.
          </p>
          <div className="flex gap-6 text-xs text-gray-400 dark:text-slate-500">
            <a
              href="mailto:jeff@ai-identity.co?subject=Privacy%20Inquiry"
              className="hover:text-gray-600 dark:hover:text-slate-300"
            >
              Privacy
            </a>
            <a
              href="mailto:jeff@ai-identity.co?subject=Terms%20Inquiry"
              className="hover:text-gray-600 dark:hover:text-slate-300"
            >
              Terms
            </a>
            <a
              href="https://api.ai-identity.co/docs#security"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-gray-600 dark:hover:text-slate-300"
            >
              Security
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
