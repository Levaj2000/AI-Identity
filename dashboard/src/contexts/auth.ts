import { createContext } from 'react'

export interface AuthUser {
  id: string
  email: string
  role: string
  tier: string
  requests_this_month: number
  org_id: string | null
}

export interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (email: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
