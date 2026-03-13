import { useCallback, useEffect, useReducer } from 'react'
import { getAgent } from '../services/api/agents'
import { listKeys } from '../services/api/keys'
import { isApiError } from '../services/api/client'
import type { Agent, AgentKey, ApiError } from '../types/api'

// ─── State ──────────────────────────────────────────────────────

interface KeysState {
  agent: Agent | null
  keys: AgentKey[]
  totalKeys: number
  isLoading: boolean
  error: ApiError | null
  notFound: boolean
}

type KeysAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; agent: Agent; keys: AgentKey[]; totalKeys: number }
  | { type: 'FETCH_ERROR'; error: ApiError }
  | { type: 'NOT_FOUND' }

const INITIAL_STATE: KeysState = {
  agent: null,
  keys: [],
  totalKeys: 0,
  isLoading: true,
  error: null,
  notFound: false,
}

function keysReducer(state: KeysState, action: KeysAction): KeysState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, isLoading: true, error: null, notFound: false }
    case 'FETCH_SUCCESS':
      return {
        agent: action.agent,
        keys: action.keys,
        totalKeys: action.totalKeys,
        isLoading: false,
        error: null,
        notFound: false,
      }
    case 'FETCH_ERROR':
      return { ...state, isLoading: false, error: action.error }
    case 'NOT_FOUND':
      return { ...INITIAL_STATE, isLoading: false, notFound: true }
  }
}

// ─── Hook ───────────────────────────────────────────────────────

interface UseAgentKeysReturn extends KeysState {
  refetch: () => void
}

/**
 * Data hook for the Agent Keys page.
 *
 * Fetches the agent and all its keys in parallel. Keys are fetched
 * unfiltered so filtering can happen client-side without refetching.
 * Distinguishes 404 (agent not found) from other errors.
 */
export function useAgentKeys(id: string | undefined): UseAgentKeysReturn {
  const [state, dispatch] = useReducer(keysReducer, INITIAL_STATE)

  const fetchData = useCallback(() => {
    if (!id) {
      dispatch({ type: 'NOT_FOUND' })
      return
    }

    let cancelled = false
    dispatch({ type: 'FETCH_START' })

    Promise.all([getAgent(id), listKeys(id)])
      .then(([agent, keyList]) => {
        if (!cancelled) {
          dispatch({
            type: 'FETCH_SUCCESS',
            agent,
            keys: keyList.items,
            totalKeys: keyList.total,
          })
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

    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    const cleanup = fetchData()
    return cleanup
  }, [fetchData])

  return {
    ...state,
    refetch: fetchData,
  }
}
