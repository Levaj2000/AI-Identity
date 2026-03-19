import { useCallback, useEffect, useState } from 'react'
import { AuthContext } from './auth'
import type { AuthUser } from './auth'
import { apiFetch, setApiKey, clearApiKey, getApiKey } from '../services/api/client'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount, check if we have a stored API key and validate it
  useEffect(() => {
    async function validateSession() {
      const key = getApiKey()
      if (!key) {
        setLoading(false)
        return
      }

      try {
        const profile = await apiFetch<AuthUser>('/api/v1/auth/me')
        setUser(profile)
      } catch {
        // Stored key is invalid — clear it
        clearApiKey()
      } finally {
        setLoading(false)
      }
    }

    validateSession()
  }, [])

  const login = useCallback(async (email: string) => {
    // Call login endpoint (no auth header needed — email is in body)
    const profile = await apiFetch<AuthUser>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })

    // Store the email as the API key (MVP auth)
    setApiKey(email)
    setUser(profile)
  }, [])

  const logout = useCallback(() => {
    clearApiKey()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  )
}
