import { API_BASE_URL, API_KEY } from '../config/api'
import type { ApiError } from '../types/api'

/**
 * Typed fetch wrapper that prepends the API base URL, injects the
 * X-API-Key header, and parses JSON automatically.
 *
 * Throws an ApiError on non-2xx responses.
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  // Inject auth for API routes (skip for /health which is public)
  if (path.startsWith('/api/')) {
    headers['X-API-Key'] = API_KEY
  }

  const response = await fetch(url, { ...options, headers })

  if (!response.ok) {
    let message = response.statusText
    let code = 'UNKNOWN'

    try {
      const body = await response.json()
      message = body.detail || body.message || message
      code = body.error || body.code || code
    } catch {
      // Response body wasn't JSON — keep defaults
    }

    const error: ApiError = {
      status: response.status,
      code,
      message,
    }
    throw error
  }

  return response.json() as Promise<T>
}
