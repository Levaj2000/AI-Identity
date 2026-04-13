/**
 * API configuration — reads from Vite environment variables.
 *
 * Set in your .env (or Vercel dashboard) to override:
 *   VITE_API_BASE_URL — Local dev: http://localhost:8001 / Prod: https://api.ai-identity.co
 *   VITE_API_KEY      — User API key for authentication (dev: test-dev-key-12345678)
 */

const PROD_API_URL = 'https://api.ai-identity.co'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || PROD_API_URL

export const API_KEY: string = import.meta.env.VITE_API_KEY || 'test-dev-key-12345678'

export const GATEWAY_URL: string =
  import.meta.env.VITE_GATEWAY_URL || 'https://gateway.ai-identity.co'

export const ENDPOINTS = {
  HEALTH: '/health',
  AGENTS: '/api/v1/agents',
  AUDIT: '/api/v1/audit',
  DOCS: `${import.meta.env.VITE_API_BASE_URL || PROD_API_URL}/docs`,
  GITHUB: 'https://github.com/Levaj2000/AI-Identity',
} as const
