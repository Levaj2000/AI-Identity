import { API_BASE_URL } from './config/api'

const API_DOCS_URL = `${API_BASE_URL}/docs`

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-[Inter,system-ui,sans-serif]">
      {/* Hero */}
      <main className="flex flex-col items-center justify-center min-h-screen px-6">
        <div className="max-w-2xl text-center space-y-8">
          {/* Logo / Brand */}
          <div className="space-y-2">
            <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
              <span className="text-indigo-500">AI</span> Identity
            </h1>
            <p className="text-xl font-medium text-slate-400 sm:text-2xl">
              Identity for AI agents.
            </p>
          </div>

          {/* Value Prop */}
          <p className="mx-auto max-w-xl text-lg leading-relaxed text-slate-400">
            Per-agent API keys, scoped permissions, and audit trails. Know which agent did what.
            Deploy in 15 minutes, not 15 weeks.
          </p>

          {/* Feature Pills */}
          <div className="flex flex-wrap justify-center gap-3">
            {[
              'Per-agent API keys',
              'Scoped permissions',
              'Immutable audit trail',
              'Key rotation with grace periods',
              'Fail-closed gateway',
            ].map((feature) => (
              <span
                key={feature}
                className="rounded-full border border-slate-700/50 bg-slate-800/60 px-4 py-2 text-sm text-slate-300"
              >
                {feature}
              </span>
            ))}
          </div>

          {/* CTA */}
          <div className="flex flex-col justify-center gap-4 pt-4 sm:flex-row">
            <a
              href={API_DOCS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-indigo-500"
            >
              Explore the API
              <span aria-hidden="true">&rarr;</span>
            </a>
            <a
              href="https://github.com/Levaj2000/AI-Identity"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-6 py-3 font-semibold text-slate-200 transition-colors hover:bg-slate-700"
            >
              View on GitHub
            </a>
          </div>

          {/* Coming Soon Badge */}
          <div className="pt-6">
            <span className="inline-flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400"></span>
              </span>
              Dashboard coming soon
            </span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="absolute bottom-0 w-full py-6 text-center text-sm text-slate-600">
        <p>&copy; {new Date().getFullYear()} AI Identity. All rights reserved.</p>
      </footer>
    </div>
  )
}

export default App
