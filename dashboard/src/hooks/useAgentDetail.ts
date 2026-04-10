import { useCallback, useEffect, useReducer } from 'react'
import { getAgent } from '../services/api/agents'
import { isApiError } from '../services/api/client'
import type { Agent, ApiError } from '../types/api'

// ─── State ──────────────────────────────────────────────────────

interface DetailState {
  agent: Agent | null
  isLoading: boolean
  error: ApiError | null
  notFound: boolean
}

type DetailAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; agent: Agent }
  | { type: 'FETCH_ERROR'; error: ApiError }
  | { type: 'NOT_FOUND' }

const INITIAL_STATE: DetailState = {
  agent: null,
  isLoading: true,
  error: null,
  notFound: false,
}

function detailReducer(state: DetailState, action: DetailAction): DetailState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, isLoading: true, error: null, notFound: false }
    case 'FETCH_SUCCESS':
      return { agent: action.agent, isLoading: false, error: null, notFound: false }
    case 'FETCH_ERROR':
      return { ...state, isLoading: false, error: action.error }
    case 'NOT_FOUND':
      return { agent: null, isLoading: false, error: null, notFound: true }
  }
}

// ─── Hook ───────────────────────────────────────────────────────

interface UseAgentDetailReturn extends DetailState {
  refetch: () => void
}

/**
 * Data hook for the Agent detail page.
 *
 * Fetches a single agent by ID. Distinguishes 404 (not found) from other errors.
 * Exposes a `refetch` callback for reloading after mutations.
 */
export function useAgentDetail(id: string | undefined): UseAgentDetailReturn {
  const [state, dispatch] = useReducer(detailReducer, INITIAL_STATE)

  const fetchAgent = useCallback(() => {
    if (!id) {
      dispatch({ type: 'NOT_FOUND' })
      return
    }

    let cancelled = false
    dispatch({ type: 'FETCH_START' })

    getAgent(id)
      .then((agent) => {
        if (!cancelled) {
          dispatch({ type: 'FETCH_SUCCESS', agent })
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (isApiError(err) && err.status === 404) {
          dispatch({ type: 'NOT_FOUND' })
        } else {
          dispatch({
            type: 'FETCH_ERROR',
            error: isApiError(err)
              ? err
              : { status: 0, code: 'NETWORK_ERROR', message: String(err) },
          })
        }
      })

    // Return cleanup to set cancelled flag
    return () => {
      cancelled = true
    }
  }, [id])

  // Fetch on mount and when ID changes
  useEffect(() => {
    const cleanup = fetchAgent()
    return cleanup
  }, [fetchAgent])

  return {
    ...state,
    refetch: fetchAgent,
  }
}
