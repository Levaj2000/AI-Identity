/**
 * API configuration — reads the base URL from Vite environment variables.
 *
 * Set VITE_API_BASE_URL in your .env (or Vercel dashboard) to override:
 *   - Local dev:  http://localhost:8001  (default, also proxied by Vite)
 *   - Production: https://ai-identity-api.onrender.com
 */

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'
