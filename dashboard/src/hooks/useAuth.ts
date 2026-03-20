import { useContext } from 'react'
import { AuthContext } from '../contexts/auth'
import type { AuthContextValue } from '../contexts/auth'

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
