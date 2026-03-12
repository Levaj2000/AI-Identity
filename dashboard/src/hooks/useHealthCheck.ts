import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/fetch'
import { ENDPOINTS } from '../config/api'
import type { HealthResponse } from '../types/api'

interface HealthState {
  isHealthy: boolean | null
  version: string | null
  isChecking: boolean
}

/** Pings GET /health on mount. Returns connectivity + version info. */
export function useHealthCheck(): HealthState {
  const [state, setState] = useState<HealthState>({
    isHealthy: null,
    version: null,
    isChecking: true,
  })

  useEffect(() => {
    let cancelled = false

    apiFetch<HealthResponse>(ENDPOINTS.HEALTH)
      .then((data) => {
        if (!cancelled) {
          setState({
            isHealthy: data.status === 'ok',
            version: data.version,
            isChecking: false,
          })
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState({ isHealthy: false, version: null, isChecking: false })
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return state
}
