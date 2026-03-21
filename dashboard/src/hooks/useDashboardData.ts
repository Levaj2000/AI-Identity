import { useEffect, useState } from 'react'
import { listAgents } from '../services/api/agents'
import { isApiError } from '../services/api/client'
import { useAuth } from './useAuth'
import type { Agent, ApiError, DashboardStats } from '../types/api'

interface DashboardData {
  stats: DashboardStats
  recentAgents: Agent[]
  isLoading: boolean
  error: ApiError | null
  isEmpty: boolean
}

const EMPTY_STATS: DashboardStats = {
  totalAgents: 0,
  activeAgents: 0,
  suspendedAgents: 0,
  revokedAgents: 0,
}

/** Fetches agents and computes dashboard stats client-side. */
export function useDashboardData(): DashboardData {
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS)
  const [recentAgents, setRecentAgents] = useState<Agent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    // Wait for auth to be ready before fetching
    if (!user) return

    let cancelled = false

    listAgents({ limit: 100 })
      .then((data) => {
        if (cancelled) return

        const items = data.items
        setStats({
          totalAgents: data.total,
          activeAgents: items.filter((a) => a.status === 'active').length,
          suspendedAgents: items.filter((a) => a.status === 'suspended').length,
          revokedAgents: items.filter((a) => a.status === 'revoked').length,
        })

        const sorted = [...items].sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
        )
        setRecentAgents(sorted.slice(0, 5))
        setIsLoading(false)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            isApiError(err) ? err : { status: 0, code: 'NETWORK_ERROR', message: String(err) },
          )
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [user])

  return {
    stats,
    recentAgents,
    isLoading,
    error,
    isEmpty: !isLoading && !error && stats.totalAgents === 0,
  }
}
