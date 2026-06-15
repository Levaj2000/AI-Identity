interface HealthIndicatorProps {
  isHealthy: boolean | null
  version: string | null
}

export function HealthIndicator({ isHealthy, version }: HealthIndicatorProps) {
  const dotColor = isHealthy === null ? 'bg-subtle' : isHealthy ? 'bg-success' : 'bg-danger'

  const pingColor = isHealthy === null ? 'bg-subtle' : isHealthy ? 'bg-success' : 'bg-danger'

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
      <span className="text-sm text-subtle">{label}</span>
      {version && <span className="text-xs text-faint">v{version}</span>}
    </div>
  )
}
