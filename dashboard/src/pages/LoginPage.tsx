import { SignIn, useUser } from '@clerk/react'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

export function LoginPage() {
  const { isSignedIn, isLoaded } = useUser()
  const navigate = useNavigate()

  // If already signed in, redirect to dashboard
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate('/dashboard', { replace: true })
    }
  }, [isLoaded, isSignedIn, navigate])

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4 font-[Inter,system-ui,sans-serif]">
      {/* Gradient accent line */}
      <div className="absolute top-0 left-0 right-0">
        <div className="h-[2px] w-full bg-gradient-to-r from-[#F59E0B] via-[#F59E0B]/50 to-transparent" />
      </div>

      {/* Logo */}
      <a href="https://ai-identity.co" className="flex items-center gap-2 mb-10">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-[#F59E0B]">
          <rect x="3" y="12" width="4" height="8" rx="1" fill="currentColor" opacity="0.6" />
          <rect x="10" y="8" width="4" height="12" rx="1" fill="currentColor" opacity="0.8" />
          <rect x="17" y="4" width="4" height="16" rx="1" fill="currentColor" />
        </svg>
        <span className="text-2xl font-semibold text-[#F59E0B]">AI Identity</span>
      </a>

      {/* Clerk SignIn widget */}
      <SignIn
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'bg-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/10 rounded-2xl',
          },
        }}
        routing="hash"
        forceRedirectUrl="/dashboard"
      />

      {/* Try Demo + Contact Sales */}
      <div className="mt-8 text-center space-y-2">
        <p className="text-gray-500 text-sm">
          Want to see it in action?{' '}
          <a href="/demo" className="text-[#F59E0B] hover:underline font-medium">
            Try the Live Demo &rarr;
          </a>
        </p>
        <p className="text-gray-500 text-sm">
          Need an enterprise plan?{' '}
          <a
            href="mailto:jeff@ai-identity.co?subject=Enterprise%20Plan%20Inquiry"
            className="text-[#F59E0B] hover:underline font-medium"
          >
            Contact Sales
          </a>
        </p>
      </div>

      {/* Back to site */}
      <a
        href="https://ai-identity.co"
        className="mt-4 text-sm text-gray-600 hover:text-gray-400 transition-colors"
      >
        &larr; Back to ai-identity.co
      </a>
    </div>
  )
}
