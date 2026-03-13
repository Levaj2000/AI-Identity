import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ─── Mock localStorage ───────────────────────────────────────────

const store: Record<string, string> = {}
const mockLocalStorage = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    store[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete store[key]
  }),
  clear: vi.fn(() => {
    for (const key of Object.keys(store)) delete store[key]
  }),
  get length() {
    return Object.keys(store).length
  },
  key: vi.fn(() => null),
}

vi.stubGlobal('localStorage', mockLocalStorage)

// Import after mocks are in place
import { parseErrorResponse, isApiError, toQueryString, getApiKey, apiFetch } from '../api/client'

// ─── Fetch mock ──────────────────────────────────────────────────

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
  mockLocalStorage.clear()
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ─── parseErrorResponse ──────────────────────────────────────────

describe('parseErrorResponse', () => {
  it('parses FastAPI detail string errors', async () => {
    const response = new Response(JSON.stringify({ detail: 'Agent not found' }), {
      status: 404,
      statusText: 'Not Found',
    })
    const err = await parseErrorResponse(response)
    expect(err).toEqual({ status: 404, code: 'API_ERROR', message: 'Agent not found' })
  })

  it('parses FastAPI validation errors (detail array)', async () => {
    const body = {
      detail: [
        { loc: ['body', 'name'], msg: 'Field required', type: 'missing' },
        { loc: ['body', 'capabilities', 0], msg: 'Invalid value', type: 'value_error' },
      ],
    }
    const response = new Response(JSON.stringify(body), {
      status: 422,
      statusText: 'Unprocessable',
    })
    const err = await parseErrorResponse(response)
    expect(err.status).toBe(422)
    expect(err.code).toBe('VALIDATION_ERROR')
    expect(err.message).toContain('body.name: Field required')
    expect(err.message).toContain('body.capabilities.0: Invalid value')
  })

  it('handles non-JSON responses gracefully', async () => {
    const response = new Response('Internal Server Error', {
      status: 500,
      statusText: 'Internal Server Error',
    })
    const err = await parseErrorResponse(response)
    expect(err).toEqual({
      status: 500,
      code: 'UNKNOWN',
      message: 'Internal Server Error',
    })
  })

  it('parses {message, code} error format', async () => {
    const body = { message: 'Rate limit exceeded', code: 'RATE_LIMITED' }
    const response = new Response(JSON.stringify(body), {
      status: 429,
      statusText: 'Too Many Requests',
    })
    const err = await parseErrorResponse(response)
    expect(err).toEqual({
      status: 429,
      code: 'RATE_LIMITED',
      message: 'Rate limit exceeded',
    })
  })

  it('handles empty response body', async () => {
    const response = new Response('', { status: 503, statusText: 'Service Unavailable' })
    const err = await parseErrorResponse(response)
    expect(err.status).toBe(503)
    expect(err.code).toBe('UNKNOWN')
  })
})

// ─── isApiError ──────────────────────────────────────────────────

describe('isApiError', () => {
  it('returns true for valid ApiError objects', () => {
    expect(isApiError({ status: 404, code: 'NOT_FOUND', message: 'Not found' })).toBe(true)
  })

  it('returns false for regular Error objects', () => {
    expect(isApiError(new Error('network error'))).toBe(false)
  })

  it('returns false for null/undefined', () => {
    expect(isApiError(null)).toBe(false)
    expect(isApiError(undefined)).toBe(false)
  })

  it('returns false for partial objects', () => {
    expect(isApiError({ status: 404 })).toBe(false)
    expect(isApiError({ status: 404, code: 'ERR' })).toBe(false)
  })
})

// ─── toQueryString ───────────────────────────────────────────────

describe('toQueryString', () => {
  it('builds a query string from params', () => {
    expect(toQueryString({ limit: 10, offset: 0 })).toBe('?limit=10&offset=0')
  })

  it('omits undefined and null values', () => {
    expect(toQueryString({ status: 'active', capability: undefined, limit: null })).toBe(
      '?status=active',
    )
  })

  it('returns empty string when no params', () => {
    expect(toQueryString({})).toBe('')
    expect(toQueryString({ a: undefined })).toBe('')
  })

  it('handles boolean values', () => {
    expect(toQueryString({ verbose: true })).toBe('?verbose=true')
  })
})

// ─── getApiKey ───────────────────────────────────────────────────

describe('getApiKey', () => {
  it('returns localStorage key when available', () => {
    store['ai-identity-api-key'] = 'stored-key'
    expect(getApiKey()).toBe('stored-key')
  })

  it('falls back to env var when localStorage is empty', () => {
    // With no localStorage value, falls back to VITE_API_KEY or empty
    const key = getApiKey()
    expect(typeof key).toBe('string')
  })
})

// ─── apiFetch ────────────────────────────────────────────────────

describe('apiFetch', () => {
  it('injects X-API-Key header for /api/ routes', async () => {
    store['ai-identity-api-key'] = 'my-test-key'
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), {
        status: 200,
      }),
    )

    await apiFetch('/api/v1/agents')

    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers['X-API-Key']).toBe('my-test-key')
  })

  it('skips auth header for /health', async () => {
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }))

    await apiFetch('/health')

    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers['X-API-Key']).toBeUndefined()
  })

  it('throws typed ApiError on non-2xx responses', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Forbidden' }), {
        status: 403,
        statusText: 'Forbidden',
      }),
    )

    await expect(apiFetch('/api/v1/agents')).rejects.toEqual(
      expect.objectContaining({
        status: 403,
        message: 'Forbidden',
      }),
    )
  })

  it('sends JSON body and Content-Type for POST requests', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ agent: {}, api_key: 'aid_sk_test' }), { status: 201 }),
    )

    await apiFetch('/api/v1/agents', {
      method: 'POST',
      body: JSON.stringify({ name: 'Test Agent' }),
    })

    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.method).toBe('POST')
    expect(opts.body).toBe('{"name":"Test Agent"}')
    expect(opts.headers['Content-Type']).toBe('application/json')
  })

  it('does not set Content-Type for GET requests (no body)', async () => {
    mockFetch.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }))

    await apiFetch('/api/v1/agents')

    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers['Content-Type']).toBeUndefined()
  })

  it('handles 204 No Content responses', async () => {
    mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const result = await apiFetch('/api/v1/agents/123')
    expect(result).toBeUndefined()
  })

  it('throws validation error with joined field messages', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: [{ loc: ['body', 'name'], msg: 'Field required', type: 'missing' }],
        }),
        { status: 422, statusText: 'Unprocessable Entity' },
      ),
    )

    await expect(apiFetch('/api/v1/agents', { method: 'POST', body: '{}' })).rejects.toEqual(
      expect.objectContaining({
        status: 422,
        code: 'VALIDATION_ERROR',
        message: 'body.name: Field required',
      }),
    )
  })
})
