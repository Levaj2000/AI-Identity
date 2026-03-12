/**
 * API configuration — reads from Vite environment variables.
 *
 * Set in your .env (or Vercel dashboard) to override:
 *   VITE_API_BASE_URL — Local dev: http://localhost:8001 / Prod: https://ai-identity-api.onrender.com
 *   VITE_API_KEY      — User API key for authentication (dev: test-dev-key-12345678)
 */

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

export const API_KEY: string = import.meta.env.VITE_API_KEY || 'test-dev-key-12345678'

export const ENDPOINTS = {
  HEALTH: '/health',
  AGENTS: '/api/v1/agents',
  AUDIT: '/api/v1/audit',
  DOCS: `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/docs`,
  GITHUB: 'https://github.com/Levaj2000/AI-Identity',
} as const
