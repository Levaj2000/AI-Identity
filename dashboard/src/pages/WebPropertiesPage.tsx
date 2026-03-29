export function WebPropertiesPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Web Properties</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Infrastructure services and deployed properties
        </p>
      </div>

      {/* Services Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Landing Page */}
        <ServiceCard
          name="Landing Page"
          description="Marketing site & early-access signup"
          platform="Vercel"
          stack="Next.js"
          region="Global (Edge)"
          url="https://ai-identity.co"
          status="live"
          color="black"
        />

        {/* Dashboard */}
        <ServiceCard
          name="Dashboard"
          description="CEO dashboard & agent management console"
          platform="Vercel"
          stack="React + TypeScript + Tailwind"
          region="Global (Edge)"
          url="https://dashboard.ai-identity.co"
          status="live"
          color="black"
        />

        {/* Identity API */}
        <ServiceCard
          name="Identity API"
          description="Core API — agents, keys, auth, billing"
          platform="Render"
          stack="Python 3.11 / FastAPI"
          region="Oregon"
          plan="Starter"
          url="https://ai-identity-api.onrender.com"
          healthCheck="/health"
          status="live"
          color="blue"
        />

        {/* Proxy Gateway */}
        <ServiceCard
          name="Proxy Gateway"
          description="Rate limiting, policy enforcement, request proxying"
          platform="Render"
          stack="Python 3.11 / FastAPI"
          region="Oregon"
          plan="Starter"
          url="https://ai-identity-gateway.onrender.com"
          healthCheck="/health"
          status="live"
          color="blue"
        />

        {/* Database */}
        <ServiceCard
          name="Database"
          description="Primary datastore — users, agents, audit logs"
          platform="Neon"
          stack="PostgreSQL"
          region="US East"
          status="live"
          color="green"
        />

        {/* Auth */}
        <ServiceCard
          name="Authentication"
          description="User auth, SSO, session management"
          platform="Clerk"
          stack="OAuth 2.0 / JWT"
          status="live"
          color="purple"
        />

        {/* Redis / Upstash */}
        <ServiceCard
          name="Redis"
          description="Cache, rate-limit state, session store"
          platform="Upstash"
          stack="Redis"
          region="Global"
          consoleUrl="https://console.upstash.com/redis/2eebd691-6259-446b-b7fe-db44371a6989?teamid=0"
          status="live"
          color="red"
        />
      </div>

      {/* Architecture Notes */}
      <div className="bg-white dark:bg-[#111113] border border-gray-200 dark:border-[#1a1a1d] rounded-xl p-5">
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
          Architecture Notes
        </h3>
        <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
          <li className="flex items-start gap-2">
            <span className="text-gray-400 mt-0.5">&#8226;</span>
            API and Gateway both run on Render Starter tier with auto-deploy from{' '}
            <code className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-[#1a1a1d] rounded">
              main
            </code>{' '}
            branch
          </li>
          <li className="flex items-start gap-2">
            <span className="text-gray-400 mt-0.5">&#8226;</span>
            Dashboard and Landing Page deploy via Vercel with preview deploys on every PR
          </li>
          <li className="flex items-start gap-2">
            <span className="text-gray-400 mt-0.5">&#8226;</span>
            Rate limiter Phase 1 uses in-memory deques; Phase 2 migrates to Upstash Redis sorted
            sets
          </li>
          <li className="flex items-start gap-2">
            <span className="text-gray-400 mt-0.5">&#8226;</span>
            UptimeRobot monitors{' '}
            <code className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-[#1a1a1d] rounded">
              /health
            </code>{' '}
            endpoints on API and Gateway
          </li>
        </ul>
      </div>
    </div>
  )
}

// ── Helper Components ───────────────────────────────────────────────

const platformColors: Record<string, string> = {
  black: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  red: 'bg-red-500/10 text-red-400 border-red-500/20',
}

function ServiceCard({
  name,
  description,
  platform,
  stack,
  region,
  plan,
  url,
  consoleUrl,
  healthCheck,
  status,
  color,
}: {
  name: string
  description: string
  platform: string
  stack: string
  region?: string
  plan?: string
  url?: string
  consoleUrl?: string
  healthCheck?: string
  status: 'live' | 'planned' | 'down'
  color: string
}) {
  const statusStyles = {
    live: 'bg-emerald-400',
    planned: 'bg-yellow-400',
    down: 'bg-red-400',
  }

  return (
    <div className="bg-white dark:bg-[#111113] border border-gray-200 dark:border-[#1a1a1d] rounded-xl p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">{name}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">{description}</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <span className={`w-2 h-2 rounded-full ${statusStyles[status]}`} />
          {status === 'live' ? 'Live' : status === 'planned' ? 'Planned' : 'Down'}
        </span>
      </div>

      {/* Details */}
      <div className="space-y-2 flex-1">
        <DetailRow label="Platform">
          <span
            className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium border ${platformColors[color] || platformColors.black}`}
          >
            {platform}
          </span>
        </DetailRow>
        <DetailRow label="Stack">{stack}</DetailRow>
        {region && <DetailRow label="Region">{region}</DetailRow>}
        {plan && <DetailRow label="Plan">{plan}</DetailRow>}
        {healthCheck && <DetailRow label="Health Check">{healthCheck}</DetailRow>}
      </div>

      {/* Links */}
      {(url || consoleUrl) && (
        <div className="mt-4 pt-3 border-t border-gray-100 dark:border-[#1a1a1d] flex gap-3">
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[#F59E0B] hover:text-[#D97706] transition-colors"
            >
              Visit &rarr;
            </a>
          )}
          {consoleUrl && (
            <a
              href={consoleUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[#F59E0B] hover:text-[#D97706] transition-colors"
            >
              Console &rarr;
            </a>
          )}
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-400 dark:text-gray-500">{label}</span>
      <span className="text-gray-700 dark:text-gray-300">{children}</span>
    </div>
  )
}
