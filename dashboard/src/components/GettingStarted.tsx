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
    <div className="rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/5 p-8 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
      <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
        Getting Started
      </h2>
      <p className="mb-6 text-sm text-gray-500 dark:text-[#a1a1aa]">
        Set up your first agent in three steps. See the{' '}
        <a
          href={`${API_BASE_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#F59E0B] underline underline-offset-2 hover:text-[#F59E0B] dark:text-[#F59E0B] dark:hover:text-[#F59E0B]"
        >
          API docs
        </a>{' '}
        for the full reference.
      </p>

      <div className="space-y-4">
        {steps.map((step) => (
          <div
            key={step.number}
            className="rounded-lg border border-gray-200 bg-white p-5 dark:border-[#1a1a1d] dark:bg-[#0A0A0B]/50"
          >
            <div className="mb-2 flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#F59E0B] text-xs font-bold text-[#0A0A0B]">
                {step.number}
              </span>
              <h3 className="font-medium text-gray-900 dark:text-[#e4e4e7]">{step.title}</h3>
            </div>
            <p className="mb-3 text-sm text-gray-500 dark:text-[#a1a1aa]">{step.description}</p>
            {step.code && (
              <pre className="overflow-x-auto rounded-lg bg-gray-100 p-4 font-[JetBrains_Mono,monospace] text-xs leading-relaxed text-gray-700 dark:bg-[#1a1a1d] dark:text-[#d4d4d8]">
                {step.code}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
