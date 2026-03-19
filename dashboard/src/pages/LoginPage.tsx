import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function LoginPage() {
  const [activeTab, setActiveTab] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, user } = useAuth()
  const navigate = useNavigate()

  // If already authenticated, redirect to dashboard
  if (user) {
    navigate('/dashboard', { replace: true })
    return null
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!email.trim()) {
      setError('Please enter your email')
      return
    }

    setLoading(true)
    try {
      await login(email.trim().toLowerCase())
      navigate('/dashboard', { replace: true })
    } catch {
      setError('Invalid credentials. Please check your email and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault()
    setError('Sign up is not yet available. Please contact sales@ai-identity.co for access.')
  }

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

      {/* Card */}
      <div className="w-full max-w-md bg-[#111113]/80 backdrop-blur-xl border border-[#F59E0B]/10 rounded-2xl p-8">
        {/* Tabs */}
        <div className="flex bg-[#0A0A0B] rounded-lg p-1 mb-8">
          <button
            onClick={() => {
              setActiveTab('login')
              setError('')
            }}
            className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'login'
                ? 'bg-[#F59E0B] text-[#0A0A0B]'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Log In
          </button>
          <button
            onClick={() => {
              setActiveTab('signup')
              setError('')
            }}
            className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'signup'
                ? 'bg-[#F59E0B] text-[#0A0A0B]'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {activeTab === 'login' ? (
          <form onSubmit={handleLogin}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  autoFocus
                  className="w-full px-4 py-3 bg-[#0A0A0B] border border-[#1a1a1d] rounded-lg text-white placeholder:text-gray-600 focus:outline-none focus:border-[#F59E0B]/50 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full px-4 py-3 bg-[#0A0A0B] border border-[#1a1a1d] rounded-lg text-white placeholder:text-gray-600 focus:outline-none focus:border-[#F59E0B]/50 transition-colors"
                />
                <p className="mt-1 text-xs text-gray-600">
                  Password auth coming soon. For now, just enter your registered email.
                </p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 py-3 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#0A0A0B] border-t-transparent" />
                  Verifying...
                </>
              ) : (
                'Log In'
              )}
            </button>

            <div className="mt-4 text-center">
              <a
                href="mailto:jeff@ai-identity.co?subject=Password%20Reset"
                className="text-sm text-[#F59E0B] hover:underline"
              >
                Forgot password?
              </a>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSignup}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Full Name</label>
                <input
                  type="text"
                  placeholder="Jane Smith"
                  className="w-full px-4 py-3 bg-[#0A0A0B] border border-[#1a1a1d] rounded-lg text-white placeholder:text-gray-600 focus:outline-none focus:border-[#F59E0B]/50 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Work Email</label>
                <input
                  type="email"
                  placeholder="you@company.com"
                  className="w-full px-4 py-3 bg-[#0A0A0B] border border-[#1a1a1d] rounded-lg text-white placeholder:text-gray-600 focus:outline-none focus:border-[#F59E0B]/50 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Password</label>
                <input
                  type="password"
                  placeholder="Min. 8 characters"
                  className="w-full px-4 py-3 bg-[#0A0A0B] border border-[#1a1a1d] rounded-lg text-white placeholder:text-gray-600 focus:outline-none focus:border-[#F59E0B]/50 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full mt-6 py-3 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-lg hover:bg-[#F59E0B]/80 transition-colors"
            >
              Create Account
            </button>

            <p className="mt-4 text-center text-xs text-gray-500">
              By signing up, you agree to our{' '}
              <a
                href="mailto:jeff@ai-identity.co?subject=Terms%20Inquiry"
                className="text-[#F59E0B] hover:underline"
              >
                Terms
              </a>{' '}
              and{' '}
              <a
                href="mailto:jeff@ai-identity.co?subject=Privacy%20Inquiry"
                className="text-[#F59E0B] hover:underline"
              >
                Privacy Policy
              </a>
            </p>
          </form>
        )}

        {/* Divider */}
        <div className="flex items-center gap-4 my-6">
          <div className="flex-1 h-px bg-[#1a1a1d]" />
          <span className="text-xs text-gray-500">OR</span>
          <div className="flex-1 h-px bg-[#1a1a1d]" />
        </div>

        {/* SSO buttons — coming soon */}
        <div className="space-y-3">
          <button
            disabled
            className="w-full py-3 border border-[#1a1a1d] rounded-lg text-sm text-gray-500 cursor-not-allowed opacity-50 flex items-center justify-center gap-3"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            GitHub SSO — Coming Soon
          </button>
          <button
            disabled
            className="w-full py-3 border border-[#1a1a1d] rounded-lg text-sm text-gray-500 cursor-not-allowed opacity-50 flex items-center justify-center gap-3"
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#666"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#666"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#666"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#666"
              />
            </svg>
            Google SSO — Coming Soon
          </button>
        </div>
      </div>

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
            href="mailto:sales@ai-identity.co"
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
