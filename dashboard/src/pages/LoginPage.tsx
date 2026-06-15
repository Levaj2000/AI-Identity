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
    <div className="min-h-screen bg-canvas flex flex-col items-center justify-center px-4 font-[Inter,system-ui,sans-serif]">
      {/* Gradient accent line */}
      <div className="absolute top-0 left-0 right-0">
        <div className="h-[2px] w-full bg-gradient-to-r from-brand via-brand/50 to-transparent" />
      </div>

      {/* Logo */}
      <a href="https://ai-identity.co" className="flex items-center gap-2 mb-10">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-brand">
          <rect x="3" y="12" width="4" height="8" rx="1" fill="currentColor" opacity="0.6" />
          <rect x="10" y="8" width="4" height="12" rx="1" fill="currentColor" opacity="0.8" />
          <rect x="17" y="4" width="4" height="16" rx="1" fill="currentColor" />
        </svg>
        <span className="text-2xl font-semibold text-brand">AI Identity</span>
      </a>

      {/* Clerk SignIn widget */}
      <SignIn
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'bg-surface/80 backdrop-blur-xl border border-brand/10 rounded-2xl',
          },
        }}
        routing="hash"
        forceRedirectUrl="/dashboard"
      />

      {/* Try Demo + Contact Sales */}
      <div className="mt-8 text-center space-y-2">
        <p className="text-subtle text-sm">
          Want to see it in action?{' '}
          <a href="/demo" className="text-brand hover:underline font-medium">
            Try the Live Demo &rarr;
          </a>
        </p>
        <p className="text-subtle text-sm">
          Need an enterprise plan?{' '}
          <a
            href="mailto:jeff@ai-identity.co?subject=Enterprise%20Plan%20Inquiry"
            className="text-brand hover:underline font-medium"
          >
            Contact Sales
          </a>
        </p>
      </div>

      {/* Back to site */}
      <a
        href="https://ai-identity.co"
        className="mt-4 text-sm text-faint hover:text-muted transition-colors"
      >
        &larr; Back to ai-identity.co
      </a>
    </div>
  )
}
