import { Navigate } from 'react-router-dom'
import { useUser } from '@clerk/react'

/**
 * Route guard — redirects to /login if not authenticated via Clerk.
 * Shows a loading spinner while Clerk checks the session.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isSignedIn, isLoaded } = useUser()

  if (!isLoaded) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#04070D]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#A6DAFF] border-t-transparent" />
          <p className="text-sm text-gray-500">Verifying credentials...</p>
        </div>
      </div>
    )
  }

  if (!isSignedIn) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
