import { useEffect, useState } from 'react'
import { useUser, useSession } from '@clerk/react'
import { AuthContext } from './auth'
import type { AuthUser } from './auth'
import { apiFetch, setSessionTokenGetter, clearSessionTokenGetter } from '../services/api/client'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { user: clerkUser, isLoaded: isUserLoaded } = useUser()
  const { session } = useSession()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // When Clerk session is available, register the token getter for API calls
  useEffect(() => {
    if (session) {
      setSessionTokenGetter(() => session.getToken())
    } else {
      clearSessionTokenGetter()
    }
  }, [session])

  // When Clerk user is loaded and signed in, sync with our API
  useEffect(() => {
    if (!isUserLoaded) return

    if (!clerkUser || !session) {
      setUser(null)
      setLoading(false)
      return
    }

    async function syncUser() {
      try {
        const profile = await apiFetch<AuthUser>('/api/v1/auth/me')
        setUser(profile)
      } catch {
        // User exists in Clerk but not in our API — will be auto-provisioned
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    syncUser()
  }, [clerkUser, session, isUserLoaded])

  // login/logout are now handled by Clerk — these are stubs for interface compat
  const login = async () => {
    // Clerk handles login via its SignIn component
  }

  const logout = () => {
    clearSessionTokenGetter()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  )
}
