import { useState, useEffect, useRef } from 'react'

const API_BASE = 'https://ai-identity-api.onrender.com'
const GATEWAY_BASE = 'https://ai-identity-gateway.onrender.com'

interface TerminalLine {
  type: 'command' | 'response' | 'info' | 'error' | 'success'
  text: string
}

interface DemoAgent {
  id: string
  name: string
  status: string
}

interface DemoKey {
  api_key: string
  key_prefix: string
}

export function DemoPage() {
  const [step, setStep] = useState(0)
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      type: 'info',
      text: '# Welcome to AI Identity — Interactive Demo',
    },
    {
      type: 'info',
      text: '# Walk through the full agent lifecycle: Register → Authenticate → Audit',
    },
    { type: 'info', text: '# Click the buttons below to execute each step.' },
    { type: 'info', text: '' },
  ])
  const [loading, setLoading] = useState(false)
  const [agent, setAgent] = useState<DemoAgent | null>(null)
  const [apiKey, setApiKey] = useState<DemoKey | null>(null)
  const [userKey, setUserKey] = useState('')
  const [showKeyInput, setShowKeyInput] = useState(true)
  const terminalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [lines])

  const addLines = (newLines: TerminalLine[]) => {
    setLines((prev) => [...prev, ...newLines])
  }

  const typeCommand = (cmd: string) => {
    addLines([{ type: 'command', text: `$ ${cmd}` }])
  }

  // Step 1: Health check
  const runHealthCheck = async () => {
    setLoading(true)
    typeCommand(`curl ${API_BASE}/health`)
    try {
      const res = await fetch(`${API_BASE}/health`)
      const data = await res.json()
      addLines([
        {
          type: 'response',
          text: JSON.stringify(data, null, 2),
        },
        { type: 'success', text: '✓ API is healthy and reachable' },
        { type: 'info', text: '' },
      ])
      setStep(1)
    } catch {
      addLines([
        {
          type: 'error',
          text: '✗ Could not reach API — service may be starting up',
        },
      ])
    }
    setLoading(false)
  }

  // Step 2: Create agent
  const runCreateAgent = async () => {
    if (!userKey) {
      addLines([
        {
          type: 'error',
          text: '✗ Please enter your API key above first',
        },
      ])
      return
    }
    setLoading(true)
    const agentName = `demo-agent-${Date.now().toString(36)}`
    typeCommand(
      `curl -X POST ${API_BASE}/api/v1/agents \\
  -H "X-API-Key: ${userKey.slice(0, 8)}..." \\
  -H "Content-Type: application/json" \\
  -d '{"name": "${agentName}", "capabilities": ["chat"]}'`,
    )
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents`, {
        method: 'POST',
        headers: {
          'X-API-Key': userKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: agentName,
          description: 'Interactive demo agent',
          capabilities: ['chat'],
          metadata: { source: 'demo-playground' },
        }),
      })
      const data = await res.json()
      if (res.ok) {
        setAgent({
          id: data.agent.id,
          name: data.agent.name,
          status: data.agent.status,
        })
        if (data.api_key) {
          setApiKey({
            api_key: data.api_key,
            key_prefix: data.api_key.slice(0, 16),
          })
        }
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          {
            type: 'success',
            text: `✓ Agent "${agentName}" created with ID: ${data.agent.id}`,
          },
          ...(data.api_key
            ? [
                {
                  type: 'success' as const,
                  text: `✓ API key generated: ${data.api_key.slice(0, 20)}... (save this — shown only once!)`,
                },
              ]
            : []),
          { type: 'info', text: '' },
        ])
        setStep(2)
      } else {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          {
            type: 'error',
            text: `✗ Error: ${data.error?.message || 'Failed to create agent'}`,
          },
          { type: 'info', text: '' },
        ])
      }
    } catch {
      addLines([{ type: 'error', text: '✗ Network error — check your API key' }])
    }
    setLoading(false)
  }

  // Step 3: List agents
  const runListAgents = async () => {
    setLoading(true)
    typeCommand(
      `curl ${API_BASE}/api/v1/agents?limit=5 \\
  -H "X-API-Key: ${userKey.slice(0, 8)}..."`,
    )
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents?limit=5`, {
        headers: { 'X-API-Key': userKey },
      })
      const data = await res.json()
      if (res.ok) {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          {
            type: 'success',
            text: `✓ Found ${data.total} agent(s)`,
          },
          { type: 'info', text: '' },
        ])
        setStep(3)
      } else {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          { type: 'error', text: '✗ Failed to list agents' },
        ])
      }
    } catch {
      addLines([{ type: 'error', text: '✗ Network error' }])
    }
    setLoading(false)
  }

  // Step 4: Gateway enforce — allowed request
  const runGatewayAllow = async () => {
    if (!agent) return
    setLoading(true)
    typeCommand(
      `curl -X POST "${GATEWAY_BASE}/gateway/enforce?agent_id=${agent.id}&endpoint=/v1/chat/completions&method=POST"`,
    )
    addLines([
      {
        type: 'info',
        text: '# Sending request through the gateway enforcement engine...',
      },
    ])
    try {
      const res = await fetch(
        `${GATEWAY_BASE}/gateway/enforce?agent_id=${agent.id}&endpoint=/v1/chat/completions&method=POST`,
        { method: 'POST' },
      )
      const data = await res.json()
      addLines([
        { type: 'response', text: JSON.stringify(data, null, 2) },
        {
          type: data.decision === 'allow' ? 'success' : 'info',
          text:
            data.decision === 'allow'
              ? '✓ Gateway ALLOWED — request passed policy enforcement'
              : `ℹ Gateway decision: ${data.decision} — ${data.deny_reason || data.message}`,
        },
        { type: 'info', text: '' },
      ])
    } catch {
      addLines([{ type: 'error', text: '✗ Gateway unreachable' }])
    }
    setLoading(false)

    // Now fire a denied request (management endpoint with runtime key concept)
    setTimeout(async () => {
      setLoading(true)
      typeCommand(
        `curl -X POST "${GATEWAY_BASE}/gateway/enforce?agent_id=${agent.id}&endpoint=/api/v1/agents&method=GET&key_type=runtime"`,
      )
      addLines([
        {
          type: 'info',
          text: '# Attempting to access management endpoint with a runtime key...',
        },
      ])
      try {
        const res2 = await fetch(
          `${GATEWAY_BASE}/gateway/enforce?agent_id=${agent.id}&endpoint=/api/v1/agents&method=GET&key_type=runtime`,
          { method: 'POST' },
        )
        const data2 = await res2.json()
        addLines([
          { type: 'response', text: JSON.stringify(data2, null, 2) },
          {
            type: data2.decision === 'deny' ? 'error' : 'success',
            text:
              data2.decision === 'deny'
                ? `✗ Gateway DENIED — ${data2.deny_reason || 'runtime key cannot access management endpoints'}`
                : `✓ Gateway decision: ${data2.decision}`,
          },
          {
            type: 'info',
            text: '# ↑ This is key separation in action: runtime keys are blocked from admin endpoints.',
          },
          { type: 'info', text: '' },
        ])
      } catch {
        addLines([{ type: 'error', text: '✗ Gateway unreachable' }])
      }
      setLoading(false)
      setStep(4)
    }, 500)
  }

  // Step 5: View audit log
  const runAuditLog = async () => {
    setLoading(true)
    const url = agent
      ? `${API_BASE}/api/v1/audit?agent_id=${agent.id}&limit=10`
      : `${API_BASE}/api/v1/audit?limit=10`
    typeCommand(
      `curl "${url.replace(API_BASE, API_BASE)}" \\
  -H "X-API-Key: ${userKey.slice(0, 8)}..."`,
    )
    try {
      const res = await fetch(url, {
        headers: { 'X-API-Key': userKey },
      })
      const data = await res.json()
      if (res.ok) {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          {
            type: 'success',
            text: `✓ ${data.total} audit entries — tamper-proof HMAC chain`,
          },
          { type: 'info', text: '' },
        ])
        setStep(5)
      } else {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          { type: 'error', text: '✗ Failed to fetch audit log' },
        ])
      }
    } catch {
      addLines([{ type: 'error', text: '✗ Network error' }])
    }
    setLoading(false)
  }

  // Step 6: Verify audit chain
  const runVerifyChain = async () => {
    setLoading(true)
    typeCommand(
      `curl ${API_BASE}/api/v1/audit/verify \\
  -H "X-API-Key: ${userKey.slice(0, 8)}..."`,
    )
    try {
      const res = await fetch(`${API_BASE}/api/v1/audit/verify`, {
        headers: { 'X-API-Key': userKey },
      })
      const data = await res.json()
      if (res.ok) {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          {
            type: data.valid ? 'success' : 'error',
            text: data.valid
              ? `✓ Chain intact — ${data.entries_verified} entries verified`
              : `✗ Chain broken at entry ${data.first_broken_id}`,
          },
          { type: 'info', text: '' },
          {
            type: 'info',
            text: '# 🎉 Demo complete! You just walked through the full AI Identity lifecycle.',
          },
          {
            type: 'info',
            text: '# Register agents → Authenticate with scoped keys → Audit everything.',
          },
        ])
        setStep(6)
      } else {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          { type: 'error', text: '✗ Failed to verify chain' },
        ])
      }
    } catch {
      addLines([{ type: 'error', text: '✗ Network error' }])
    }
    setLoading(false)
  }

  // Cleanup: delete demo agent
  const runCleanup = async () => {
    if (!agent) return
    setLoading(true)
    typeCommand(
      `curl -X DELETE ${API_BASE}/api/v1/agents/${agent.id} \\
  -H "X-API-Key: ${userKey.slice(0, 8)}..."`,
    )
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents/${agent.id}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': userKey },
      })
      const data = await res.json()
      if (res.ok) {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          {
            type: 'success',
            text: `✓ Demo agent revoked and cleaned up`,
          },
        ])
        setAgent(null)
        setApiKey(null)
      } else {
        addLines([
          { type: 'response', text: JSON.stringify(data, null, 2) },
          { type: 'error', text: '✗ Cleanup failed' },
        ])
      }
    } catch {
      addLines([{ type: 'error', text: '✗ Network error' }])
    }
    setLoading(false)
  }

  const steps = [
    {
      label: '1. Health Check',
      description: 'Verify the API is reachable',
      action: runHealthCheck,
      active: step === 0,
    },
    {
      label: '2. Create Agent',
      description: 'Register a new AI agent with scoped capabilities',
      action: runCreateAgent,
      active: step === 1,
    },
    {
      label: '3. List Agents',
      description: 'Retrieve all registered agents',
      action: runListAgents,
      active: step === 2,
    },
    {
      label: '4. Gateway Enforce',
      description: 'Test allow + deny through the policy engine',
      action: runGatewayAllow,
      active: step === 3,
    },
    {
      label: '5. Audit Log',
      description: 'View the tamper-proof audit trail',
      action: runAuditLog,
      active: step === 4,
    },
    {
      label: '6. Verify Chain',
      description: 'Cryptographically verify audit integrity',
      action: runVerifyChain,
      active: step === 5,
    },
  ]

  const getLineColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'command':
        return 'text-[#A6DAFF]'
      case 'response':
        return 'text-gray-300'
      case 'info':
        return 'text-gray-500'
      case 'error':
        return 'text-red-400'
      case 'success':
        return 'text-emerald-400'
    }
  }

  return (
    <div className="min-h-screen bg-[#04070D] font-[Inter,system-ui,sans-serif]">
      {/* Gradient accent line */}
      <div className="absolute top-0 left-0 right-0">
        <div className="h-[2px] w-full bg-gradient-to-r from-[#A6DAFF] via-[#A6DAFF]/50 to-transparent" />
      </div>

      {/* Header */}
      <header className="border-b border-[#1a1a1d] px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <a href="https://ai-identity.co" className="flex items-center gap-2">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" className="text-[#A6DAFF]">
              <rect x="3" y="12" width="4" height="8" rx="1" fill="currentColor" opacity="0.6" />
              <rect x="10" y="8" width="4" height="12" rx="1" fill="currentColor" opacity="0.8" />
              <rect x="17" y="4" width="4" height="16" rx="1" fill="currentColor" />
            </svg>
            <span className="text-lg font-semibold text-[#A6DAFF]">AI Identity</span>
          </a>
          <div className="flex items-center gap-4">
            <span className="rounded-full border border-[#A6DAFF]/30 bg-[#A6DAFF]/10 px-3 py-1 text-xs font-medium text-[#A6DAFF]">
              Live API Demo
            </span>
            <a href="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
              Sign In
            </a>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Title */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white md:text-4xl">
            Interactive API <span className="text-[#A6DAFF]">Playground</span>
          </h1>
          <p className="mt-2 text-gray-400">
            Execute real API calls against the live AI Identity backend. No mock data.
          </p>
        </div>

        {/* API Key Input */}
        {showKeyInput && (
          <div className="mx-auto mb-8 max-w-xl rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 p-6">
            <label className="mb-2 block text-sm font-medium text-gray-300">Your API Key</label>
            <p className="mb-3 text-xs text-gray-500">
              Enter your user API key to make authenticated requests. Don't have one?{' '}
              <a href="/login" className="text-[#A6DAFF] hover:underline">
                Sign up free
              </a>
            </p>
            <div className="flex gap-2">
              <input
                type="password"
                value={userKey}
                onChange={(e) => setUserKey(e.target.value)}
                placeholder="your-api-key-here"
                className="flex-1 rounded-lg border border-[#1a1a1d] bg-[#04070D] px-4 py-2.5 text-sm text-white placeholder:text-gray-600 focus:border-[#A6DAFF]/50 focus:outline-none"
              />
              <button
                onClick={() => {
                  if (userKey) setShowKeyInput(false)
                }}
                className="rounded-lg bg-[#A6DAFF] px-4 py-2.5 text-sm font-medium text-[#04070D] hover:bg-[#A6DAFF]/80 transition-colors"
              >
                Save
              </button>
            </div>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          {/* Steps sidebar */}
          <div className="space-y-2">
            {steps.map((s, i) => (
              <button
                key={i}
                onClick={s.action}
                disabled={loading || (!s.active && i > step)}
                className={`w-full rounded-xl border p-4 text-left transition-all ${
                  s.active
                    ? 'border-[#A6DAFF]/50 bg-[#A6DAFF]/10'
                    : i < step
                      ? 'border-emerald-500/30 bg-emerald-500/5'
                      : 'border-[#1a1a1d] bg-[#10131C]/50 opacity-50'
                } ${loading ? 'cursor-wait' : i <= step ? 'cursor-pointer hover:border-[#A6DAFF]/30' : 'cursor-not-allowed'}`}
              >
                <div className="flex items-center gap-2">
                  {i < step ? (
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : s.active ? (
                    <div className="h-2 w-2 animate-pulse rounded-full bg-[#A6DAFF]" />
                  ) : (
                    <div className="h-2 w-2 rounded-full bg-gray-600" />
                  )}
                  <span
                    className={`text-sm font-medium ${
                      s.active ? 'text-[#A6DAFF]' : i < step ? 'text-emerald-400' : 'text-gray-500'
                    }`}
                  >
                    {s.label}
                  </span>
                </div>
                <p className="mt-1 pl-5 text-xs text-gray-500">{s.description}</p>
              </button>
            ))}

            {/* Cleanup button */}
            {agent && step >= 6 && (
              <button
                onClick={runCleanup}
                disabled={loading}
                className="w-full rounded-xl border border-red-500/30 bg-red-500/5 p-4 text-left transition-all hover:border-red-500/50"
              >
                <span className="text-sm font-medium text-red-400">Clean Up Demo Agent</span>
                <p className="mt-1 text-xs text-gray-500">Revoke the agent created during demo</p>
              </button>
            )}

            {/* Reset */}
            <button
              onClick={() => {
                setStep(0)
                setLines([
                  {
                    type: 'info',
                    text: '# Session reset — ready for a new demo run',
                  },
                  { type: 'info', text: '' },
                ])
                setAgent(null)
                setApiKey(null)
              }}
              className="w-full rounded-lg border border-[#1a1a1d] px-4 py-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Reset Terminal
            </button>
          </div>

          {/* Terminal */}
          <div className="rounded-xl border border-[#1a1a1d] bg-[#04070D] overflow-hidden">
            {/* Terminal header */}
            <div className="flex items-center gap-2 border-b border-[#1a1a1d] px-4 py-3">
              <div className="h-3 w-3 rounded-full bg-red-500/80" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
              <div className="h-3 w-3 rounded-full bg-green-500/80" />
              <span className="ml-2 text-xs text-gray-500">ai-identity-demo — bash</span>
              {loading && (
                <div className="ml-auto flex items-center gap-1.5">
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#A6DAFF]" />
                  <div
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#A6DAFF]"
                    style={{ animationDelay: '0.15s' }}
                  />
                  <div
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#A6DAFF]"
                    style={{ animationDelay: '0.3s' }}
                  />
                </div>
              )}
            </div>

            {/* Terminal body */}
            <div ref={terminalRef} className="h-[500px] overflow-y-auto p-4 font-mono text-sm">
              {lines.map((line, i) => (
                <pre
                  key={i}
                  className={`whitespace-pre-wrap break-all ${getLineColor(line.type)} ${
                    line.type === 'command' ? 'mt-2 font-semibold' : ''
                  } ${line.type === 'response' ? 'ml-2 text-xs opacity-80' : ''}`}
                >
                  {line.text}
                </pre>
              ))}
              {loading && <span className="inline-block h-4 w-2 animate-pulse bg-[#A6DAFF]" />}
            </div>
          </div>
        </div>

        {/* Context cards */}
        {(agent || apiKey) && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {agent && (
              <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 p-4">
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Demo Agent
                </p>
                <p className="mt-1 text-sm font-mono text-white truncate">{agent.name}</p>
                <p className="mt-0.5 text-xs text-gray-500 font-mono truncate">{agent.id}</p>
                <span
                  className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                    agent.status === 'active'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-red-500/10 text-red-400'
                  }`}
                >
                  {agent.status}
                </span>
              </div>
            )}
            {apiKey && (
              <div className="rounded-xl border border-[#1a1a1d] bg-[#10131C]/80 p-4">
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Agent API Key
                </p>
                <p className="mt-1 text-sm font-mono text-[#A6DAFF] truncate">
                  {apiKey.key_prefix}...
                </p>
                <p className="mt-0.5 text-xs text-gray-500">Runtime key — shown only once</p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 border-t border-[#1a1a1d] pt-6 text-center">
          <p className="text-sm text-gray-500">
            All API calls hit the live production backend at{' '}
            <code className="text-[#A6DAFF]">{API_BASE}</code>
          </p>
          <div className="mt-3 flex items-center justify-center gap-4">
            <a
              href="https://ai-identity.co"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              &larr; Back to site
            </a>
            <a href="/dashboard" className="text-sm text-[#A6DAFF] hover:underline">
              Open Dashboard
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
