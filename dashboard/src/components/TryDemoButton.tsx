import { useState } from 'react'
import { createAgent } from '../services/api/agents'
import { fetchAuditLogs, verifyAuditChain } from '../services/api/forensics'
import { GATEWAY_URL } from '../config/api'
import type { AuditLogEntry } from '../types/api'

type DemoStep = 'idle' | 'creating' | 'enforcing' | 'auditing' | 'verifying' | 'done' | 'error'

const STEPS = [
  { key: 'creating', label: 'Creating demo agent', done: 'Agent created' },
  { key: 'enforcing', label: 'Sending gateway request', done: 'Policy enforced: allowed' },
  {
    key: 'auditing',
    label: 'Fetching audit trail',
    done: (n: number) => `${n} audit entries logged`,
  },
  {
    key: 'verifying',
    label: 'Verifying HMAC chain',
    done: (n: number) => `Chain verified: ${n} entries`,
  },
] as const

const ORDER: DemoStep[] = ['creating', 'enforcing', 'auditing', 'verifying', 'done']

function stepIndex(step: DemoStep): number {
  return ORDER.indexOf(step)
}

export function TryDemoButton() {
  const [step, setStep] = useState<DemoStep>('idle')
  const [agentId, setAgentId] = useState<string | null>(null)
  const [auditEntries, setAuditEntries] = useState<AuditLogEntry[]>([])
  const [chainResult, setChainResult] = useState<{
    valid: boolean
    entries_verified: number
  } | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function runDemo() {
    setStep('creating')
    setErrorMessage(null)

    try {
      // Step 1: Create demo agent
      const { agent } = await createAgent({
        name: `demo-agent-${Date.now().toString(36)}`,
        capabilities: ['chat_completion'],
        metadata: { demo: true },
      })
      setAgentId(agent.id)

      // Step 2: Fire gateway enforce request
      setStep('enforcing')
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 30000)

      const gwRes = await fetch(
        `${GATEWAY_URL}/gateway/enforce?agent_id=${agent.id}&endpoint=/v1/chat/completions&method=POST`,
        { method: 'POST', signal: controller.signal },
      )
      clearTimeout(timeout)

      if (!gwRes.ok) {
        const body = await gwRes.json().catch(() => ({}))
        throw new Error(body.message || `Gateway returned ${gwRes.status}`)
      }

      // Step 3: Fetch audit logs (500ms delay for eventual consistency)
      setStep('auditing')
      await new Promise((r) => setTimeout(r, 500))

      const logs = await fetchAuditLogs({ agent_id: agent.id, limit: 10 })
      setAuditEntries(logs.items)

      // Step 4: Verify chain
      setStep('verifying')
      const verify = await verifyAuditChain(agent.id)
      setChainResult(verify)

      setStep('done')
    } catch (err) {
      setStep('error')
      if (err instanceof DOMException && err.name === 'AbortError') {
        setErrorMessage('Gateway is warming up (free tier cold start). Try again in a moment.')
      } else {
        setErrorMessage(err instanceof Error ? err.message : String(err))
      }
    }
  }

  function reset() {
    setStep('idle')
    setAgentId(null)
    setAuditEntries([])
    setChainResult(null)
    setErrorMessage(null)
  }

  // --- Idle state ---
  if (step === 'idle') {
    return (
      <button
        onClick={runDemo}
        className="mb-6 flex w-full items-center justify-center gap-2 rounded-lg bg-[#A6DAFF] px-6 py-3 text-sm font-bold text-[#04070D] transition-all hover:bg-[#A6DAFF]/80 hover:-translate-y-0.5"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polygon points="5 3 19 12 5 21 5 3" />
        </svg>
        Try It Now — Create a demo agent in 30 seconds
      </button>
    )
  }

  // --- Error state ---
  if (step === 'error') {
    return (
      <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-5">
        <p className="mb-3 text-sm text-red-400">{errorMessage}</p>
        <button
          onClick={() => {
            reset()
            runDemo()
          }}
          className="rounded-lg bg-red-500/20 px-4 py-2 text-xs font-semibold text-red-400 transition-colors hover:bg-red-500/30"
        >
          Retry
        </button>
      </div>
    )
  }

  // --- Running / Done state ---
  const currentIdx = stepIndex(step)

  return (
    <div className="mb-6 rounded-lg border border-[#A6DAFF]/20 bg-[#04070D]/50 p-5">
      <div className="space-y-3">
        {STEPS.map((s, i) => {
          const isDone = currentIdx > i || step === 'done'
          const isActive = currentIdx === i && step !== 'done'

          let label: string
          if (isDone) {
            const d = s.done
            if (typeof d === 'function') {
              label = i === 2 ? d(auditEntries.length) : d(chainResult?.entries_verified ?? 0)
            } else {
              label = d
            }
          } else if (isActive) {
            label = `${s.label}...`
          } else {
            label = s.label
          }

          return (
            <div key={s.key} className="flex items-center gap-3">
              {isDone ? (
                <svg
                  className="h-5 w-5 shrink-0 text-emerald-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : isActive ? (
                <span className="flex h-5 w-5 items-center justify-center">
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#A6DAFF]" />
                </span>
              ) : (
                <span className="flex h-5 w-5 items-center justify-center">
                  <span className="h-2.5 w-2.5 rounded-full bg-gray-600" />
                </span>
              )}
              <span
                className={`text-sm ${isDone ? 'text-emerald-400' : isActive ? 'text-[#A6DAFF]' : 'text-gray-500'}`}
              >
                {label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Done: summary card */}
      {step === 'done' && (
        <div className="mt-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-400">
              {chainResult?.valid ? 'Chain Verified' : 'Chain Error'}
            </span>
            <span className="text-xs text-gray-400">
              {auditEntries.length} audit entries &middot; {chainResult?.entries_verified} verified
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            <a
              href={`/dashboard/forensics?agent_id=${agentId}`}
              className="inline-flex items-center gap-1 rounded-lg bg-[#A6DAFF] px-4 py-2 text-xs font-bold text-[#04070D] transition-all hover:bg-[#A6DAFF]/80"
            >
              View Full Forensics
              <span aria-hidden="true">&rarr;</span>
            </a>
            <a
              href={`/dashboard/agents/${agentId}`}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-600 px-4 py-2 text-xs font-semibold text-gray-300 transition-colors hover:border-[#A6DAFF]"
            >
              View Agent
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
