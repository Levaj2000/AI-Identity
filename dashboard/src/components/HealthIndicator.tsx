interface HealthIndicatorProps {
  isHealthy: boolean | null
  version: string | null
}

export function HealthIndicator({ isHealthy, version }: HealthIndicatorProps) {
  const dotColor = isHealthy === null ? 'bg-slate-500' : isHealthy ? 'bg-emerald-500' : 'bg-red-500'

  const pingColor =
    isHealthy === null ? 'bg-slate-400' : isHealthy ? 'bg-emerald-400' : 'bg-red-400'

  const showPing = isHealthy === null || isHealthy

  const label = isHealthy === null ? 'Checking...' : isHealthy ? 'API Connected' : 'API Unreachable'

  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-2.5 w-2.5">
        {showPing && (
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full ${pingColor} opacity-75`}
          />
        )}
        <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${dotColor}`} />
      </span>
      <span className="text-sm text-slate-400">{label}</span>
      {version && <span className="text-xs text-slate-600">v{version}</span>}
    </div>
  )
}
