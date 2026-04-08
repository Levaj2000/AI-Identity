import { API_BASE_URL, GATEWAY_URL } from '../config/api'
import { TryDemoButton } from './TryDemoButton'

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
    title: 'Point Your Agent at the Gateway',
    description:
      "Store your API key (aid_sk_...) securely — it's shown only once. Then point your agent's base URL at our gateway instead of calling OpenAI directly.",
    code: `# Instead of: https://api.openai.com/v1/chat/completions
# Point to:  ${GATEWAY_URL}/v1/chat/completions
#
# Add your API key as the X-API-Key header`,
  },
  {
    number: 3,
    title: 'Set a Policy & Run Compliance',
    description:
      'Define what your agent can do with scoped permissions, then run an automated compliance check to verify your governance posture.',
    code: `curl -s -X POST ${API_BASE_URL}/api/v1/agents/{agent_id}/policies \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"rules": {"allowed_endpoints": ["/v1/chat"]}}'`,
  },
  {
    number: 4,
    title: 'Explore AI Forensics',
    description:
      'Every gateway decision is logged in a tamper-evident HMAC chain. Use the Forensics dashboard to investigate incidents, reconstruct agent behavior, and export chain-of-custody reports.',
    code: null,
    link: { href: '/dashboard/forensics', label: 'Open Forensics Dashboard' },
  },
]

export function GettingStarted() {
  return (
    <div className="rounded-xl border border-[#A6DAFF]/20 bg-[#A6DAFF]/5 p-8 dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl">
      <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
        Getting Started
      </h2>
      <p className="mb-6 text-sm text-gray-500 dark:text-[#a1a1aa]">
        Set up your first agent in four steps — identity, policy, compliance, and forensics. See the{' '}
        <a
          href={`${API_BASE_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#A6DAFF] underline underline-offset-2 hover:text-[#A6DAFF] dark:text-[#A6DAFF] dark:hover:text-[#A6DAFF]"
        >
          API docs
        </a>{' '}
        for the full reference.
      </p>

      <TryDemoButton />

      <div className="space-y-4">
        {steps.map((step) => (
          <div
            key={step.number}
            className="rounded-lg border border-gray-200 bg-white p-5 dark:border-[#1a1a1d] dark:bg-[#04070D]/50"
          >
            <div className="mb-2 flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#A6DAFF] text-xs font-bold text-[#04070D]">
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
            {step.link && (
              <a
                href={step.link.href}
                className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-[#A6DAFF] hover:underline"
              >
                {step.link.label}
                <span aria-hidden="true">&rarr;</span>
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
