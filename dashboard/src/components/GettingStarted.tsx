import { API_BASE_URL } from '../config/api'

const steps = [
  {
    number: 1,
    title: 'Create Your First Agent',
    description: "Register an AI agent with a name and capabilities. You'll receive an API key.",
    code: `curl -s -X POST ${API_BASE_URL}/api/v1/agents \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My First Agent",
    "capabilities": ["chat_completion"]
  }'`,
  },
  {
    number: 2,
    title: 'Store Your API Key',
    description:
      "The agent's API key (aid_sk_...) is shown only once at creation. Store it securely — it cannot be retrieved later.",
    code: null,
  },
  {
    number: 3,
    title: 'Manage Keys & Permissions',
    description:
      'Rotate keys with zero downtime (24-hour grace period), revoke compromised keys instantly, and scope agent capabilities.',
    code: `curl -s -X POST ${API_BASE_URL}/api/v1/agents/{agent_id}/keys/rotate \\
  -H "X-API-Key: YOUR_KEY"`,
  },
]

export function GettingStarted() {
  return (
    <div className="rounded-xl border border-indigo-500/20 bg-slate-900/50 p-8">
      <h2 className="mb-2 text-lg font-semibold text-slate-100">Getting Started</h2>
      <p className="mb-6 text-sm text-slate-400">
        Set up your first agent in three steps. See the{' '}
        <a
          href={`${API_BASE_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-400 underline underline-offset-2 hover:text-indigo-300"
        >
          API docs
        </a>{' '}
        for the full reference.
      </p>

      <div className="space-y-4">
        {steps.map((step) => (
          <div key={step.number} className="rounded-lg border border-slate-800 bg-slate-950/50 p-5">
            <div className="mb-2 flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                {step.number}
              </span>
              <h3 className="font-medium text-slate-100">{step.title}</h3>
            </div>
            <p className="mb-3 text-sm text-slate-400">{step.description}</p>
            {step.code && (
              <pre className="overflow-x-auto rounded-lg bg-slate-800 p-4 font-[JetBrains_Mono,monospace] text-xs leading-relaxed text-slate-300">
                {step.code}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
