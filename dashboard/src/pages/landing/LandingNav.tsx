import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from '../../components/Logo'
import { ThemeToggle } from '../../components/ThemeToggle'
import { usePageProgress } from '../../hooks/useScrollProgress'

export function LandingNav() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const progress = usePageProgress()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`fixed top-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? 'border-b border-gray-200 bg-white/80 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/80'
          : 'bg-transparent'
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <Link to="/" className="flex items-center">
          <Logo variant="full" size={28} />
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-8 md:flex">
          <a
            href="#features"
            className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-slate-400 dark:hover:text-slate-200"
          >
            Features
          </a>
          <a
            href="#how-it-works"
            className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-slate-400 dark:hover:text-slate-200"
          >
            How It Works
          </a>
          <a
            href="https://ai-identity-api.onrender.com/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-slate-400 dark:hover:text-slate-200"
          >
            Docs
          </a>
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link
            to="/app"
            className="hidden rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 sm:inline-flex"
          >
            Get Started
          </Link>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-800 md:hidden"
            aria-label="Toggle menu"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              {menuOpen ? (
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              ) : (
                <path
                  fillRule="evenodd"
                  d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z"
                  clipRule="evenodd"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Scroll progress bar */}
      <div
        className="absolute bottom-0 left-0 h-[2px]"
        style={{
          width: `${progress * 100}%`,
          background: 'linear-gradient(90deg, #6366f1, #818cf8)',
          backgroundSize: '200% 100%',
          animation: progress > 0 ? 'progress-shimmer 3s linear infinite' : 'none',
          transition: 'width 0.1s ease-out',
        }}
      />

      {/* Mobile menu */}
      {menuOpen && (
        <div className="border-t border-gray-200 bg-white px-6 pb-6 pt-4 dark:border-slate-800 dark:bg-slate-950 md:hidden">
          <nav className="flex flex-col gap-4">
            <a
              href="#features"
              onClick={() => setMenuOpen(false)}
              className="text-sm font-medium text-gray-700 dark:text-slate-300"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              onClick={() => setMenuOpen(false)}
              className="text-sm font-medium text-gray-700 dark:text-slate-300"
            >
              How It Works
            </a>
            <a
              href="https://ai-identity-api.onrender.com/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-gray-700 dark:text-slate-300"
            >
              Docs
            </a>
            <Link
              to="/app"
              className="mt-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-center text-sm font-semibold text-white"
            >
              Get Started
            </Link>
          </nav>
        </div>
      )}
    </header>
  )
}
