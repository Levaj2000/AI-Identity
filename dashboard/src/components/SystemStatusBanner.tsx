import { useState, useEffect } from 'react'
import { apiFetch } from '../services/api/client'
import { useAuth } from '../hooks/useAuth'

interface HealthResponse {
  status: string
  db_latency_ms: number
  table_counts: Record<string, number>
}

interface KeyInfo {
  id: string
  rotated_at: string | null
  created_at: string
}

interface KeysResponse {
  items: KeyInfo[]
  total: number
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function MiniSparkline({ values }: { values: number[] }) {
  const max = Math.max(...values, 1)
  const width = 48
  const height = 16
  const path = values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * width
      const y = height - (v / max) * height
      return `${i === 0 ? 'M' : 'L'}${x},${y}`
    })
    .join(' ')

  return (
    <svg width={width} height={height} className="inline-block align-middle">
      <path
        d={path}
        fill="none"
        stroke="#A6DAFF"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function SystemStatusBanner() {
  const { user } = useAuth()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [lastRotation, setLastRotation] = useState<string | null>(null)
  const [latencyHistory, setLatencyHistory] = useState<number[]>([])

  useEffect(() => {
    if (!user) return
    // Fetch health (ping a few times for sparkline)
    async function loadHealth() {
      try {
        const results: number[] = []
        for (let i = 0; i < 4; i++) {
          const res = await apiFetch<HealthResponse>('/api/v1/admin/health')
          results.push(res.db_latency_ms)
          if (i === 0) setHealth(res)
        }
        setLatencyHistory(results)
      } catch {
        // non-critical
      }
    }

    // Fetch most recent key rotation
    async function loadLastRotation() {
      try {
        // Get all agents, check their keys for rotation dates
        const agents = await apiFetch<{ items: { id: string }[] }>('/api/v1/agents?limit=10')
        let mostRecent: string | null = null
        for (const agent of agents.items) {
          try {
            const keys = await apiFetch<KeysResponse>(`/api/v1/agents/${agent.id}/keys?limit=5`)
            for (const key of keys.items) {
              const date = key.rotated_at || key.created_at
              if (!mostRecent || date > mostRecent) {
                mostRecent = date
              }
            }
          } catch {
            // skip agent
          }
        }
        setLastRotation(mostRecent)
      } catch {
        // non-critical
      }
    }

    loadHealth()
    loadLastRotation()
  }, [user])

  const isHealthy = health?.status === 'healthy'
  const latency = health ? Math.round(health.db_latency_ms) : null

  return (
    <div
      className={`rounded-xl border border-l-4 border-gray-200 ${isHealthy ? 'border-l-emerald-500' : 'border-l-yellow-500'} bg-white p-5 dark:border-[#A6DAFF]/10 ${isHealthy ? 'dark:border-l-emerald-500' : 'dark:border-l-yellow-500'} dark:bg-[#10131C]/80 dark:backdrop-blur-xl`}
    >
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {/* Gateway Status */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Gateway Status
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              {isHealthy && (
                <span
                  className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75"
                  style={{ animationDuration: '2s' }}
                />
              )}
              <span
                className={`relative inline-flex h-2.5 w-2.5 rounded-full ${isHealthy ? 'bg-emerald-500' : health ? 'bg-yellow-500' : 'bg-gray-400'}`}
              />
            </span>
            <span className="font-semibold text-gray-900 dark:text-[#e4e4e7]">
              {health ? (isHealthy ? 'Operational' : 'Degraded') : '—'}
            </span>
          </div>
        </div>

        {/* API Latency */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            API Latency
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span className="font-semibold text-gray-900 dark:text-[#e4e4e7]">
              {latency !== null ? `${latency}ms` : '—'}
            </span>
            {latencyHistory.length > 1 && <MiniSparkline values={latencyHistory} />}
          </div>
        </div>

        {/* Uptime — placeholder until we have uptime tracking */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Uptime
          </p>
          <p className="mt-1 font-semibold text-emerald-500">{isHealthy ? '✓ Online' : '—'}</p>
        </div>

        {/* Last Key Rotation */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
            Last Key Rotation
          </p>
          <div className="mt-1 flex items-center gap-2">
            <svg
              className="h-4 w-4 text-gray-400 dark:text-[#71717a]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="font-semibold text-gray-900 dark:text-[#e4e4e7]">
              {lastRotation ? timeAgo(lastRotation) : 'No keys yet'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
