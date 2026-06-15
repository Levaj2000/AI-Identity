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
    <div className="rounded-xl border border-line bg-brand-soft p-8">
      <h2 className="mb-2 text-lg font-semibold text-ink">Getting Started</h2>
      <p className="mb-6 text-sm text-muted">
        Set up your first agent in four steps — identity, policy, compliance, and forensics. See the{' '}
        <a
          href={`${API_BASE_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand underline underline-offset-2 hover:text-brand"
        >
          API docs
        </a>{' '}
        for the full reference.
      </p>

      <TryDemoButton />

      <div className="space-y-4">
        {steps.map((step) => (
          <div key={step.number} className="rounded-lg border border-line bg-surface p-5">
            <div className="mb-2 flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-brand-ink">
                {step.number}
              </span>
              <h3 className="font-medium text-ink">{step.title}</h3>
            </div>
            <p className="mb-3 text-sm text-muted">{step.description}</p>
            {step.code && (
              <pre className="overflow-x-auto rounded-lg bg-inset p-4 font-[JetBrains_Mono,monospace] text-xs leading-relaxed text-muted">
                {step.code}
              </pre>
            )}
            {step.link && (
              <a
                href={step.link.href}
                className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-brand hover:underline"
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
