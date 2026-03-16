import { useState, useEffect, useRef, useCallback } from 'react'
import { useScrollReveal } from '../../hooks/useScrollReveal'

const tabs = [
  {
    label: 'cURL',
    lang: 'bash',
    code: `# 1. Create an agent with its own identity
curl -X POST https://api.ai-identity.co/v1/agents \\
  -H "X-API-Key: $DEV_KEY" \\
  -d '{"name": "billing-bot", "capabilities": ["stripe.charges"]}'

# Response → { "id": "agt_9f3a…", "api_key": "aid_sk_a7f3b9c2…" }

# 2. Route requests through the gateway
curl https://gateway.ai-identity.co/v1/charges \\
  -H "X-API-Key: aid_sk_a7f3b9c2…" \\
  -d '{"amount": 2000, "currency": "usd"}'

# 3. Check the audit trail
curl https://api.ai-identity.co/v1/audit?agent_id=agt_9f3a… \\
  -H "X-API-Key: $DEV_KEY"`,
  },
  {
    label: 'Python',
    lang: 'python',
    code: `import httpx

API = "https://api.ai-identity.co/v1"
GATEWAY = "https://gateway.ai-identity.co/v1"
DEV_KEY = "your_dev_key"

# 1. Create an agent with its own identity
agent = httpx.post(f"{API}/agents", headers={"X-API-Key": DEV_KEY},
    json={"name": "billing-bot", "capabilities": ["stripe.charges"]}
).json()

agent_key = agent["api_key"]  # aid_sk_a7f3b9c2…

# 2. Route requests through the gateway
resp = httpx.post(f"{GATEWAY}/charges",
    headers={"X-API-Key": agent_key},
    json={"amount": 2000, "currency": "usd"}
)

# 3. Check the audit trail
logs = httpx.get(f"{API}/audit",
    headers={"X-API-Key": DEV_KEY},
    params={"agent_id": agent["id"]}
).json()`,
  },
]

/** Tokenize a line of code for syntax highlighting */
function tokenizeLine(line: string, lang: string): React.ReactNode[] {
  const tokens: React.ReactNode[] = []

  if (lang === 'bash') {
    // Comments
    if (line.trimStart().startsWith('#')) {
      tokens.push(
        <span key="c" className="text-gray-500 italic">
          {line}
        </span>,
      )
      return tokens
    }
    // Process tokens with regex
    const regex =
      /(curl|grep|echo|cat|cd|pip|npm|python)|\$\w+|"[^"]*"|'[^']*'|(https?:\/\/[^\s"'\\]+)|(--?\w[\w-]*)|(\\.)/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(line)) !== null) {
      // Text before match
      if (match.index > lastIndex) {
        tokens.push(<span key={lastIndex}>{line.slice(lastIndex, match.index)}</span>)
      }
      const m = match[0]
      if (/^(curl|grep|echo|cat|cd|pip|npm|python)$/.test(m)) {
        tokens.push(
          <span key={match.index} className="text-amber-300 font-semibold">
            {m}
          </span>,
        )
      } else if (m.startsWith('$')) {
        tokens.push(
          <span key={match.index} className="text-purple-400">
            {m}
          </span>,
        )
      } else if (m.startsWith('"') || m.startsWith("'")) {
        tokens.push(
          <span key={match.index} className="text-emerald-400">
            {m}
          </span>,
        )
      } else if (m.startsWith('http')) {
        tokens.push(
          <span key={match.index} className="text-sky-400 underline decoration-sky-400/30">
            {m}
          </span>,
        )
      } else if (m.startsWith('-')) {
        tokens.push(
          <span key={match.index} className="text-indigo-400">
            {m}
          </span>,
        )
      } else {
        tokens.push(
          <span key={match.index} className="text-gray-400">
            {m}
          </span>,
        )
      }
      lastIndex = match.index + m.length
    }
    if (lastIndex < line.length) {
      tokens.push(<span key={lastIndex}>{line.slice(lastIndex)}</span>)
    }
  } else {
    // Python
    if (line.trimStart().startsWith('#')) {
      tokens.push(
        <span key="c" className="text-gray-500 italic">
          {line}
        </span>,
      )
      return tokens
    }
    const regex =
      /(import|from|as|def|return|class|if|else|for|in|with|try|except|raise|and|or|not|True|False|None)(?=\s|$|[(.:])|(\w+)\s*(?=\()|"[^"]*"|'[^']*'|f"[^"]*"|f'[^']*'|(https?:\/\/[^\s"'\\]+)|\b(\d+)\b/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(line)) !== null) {
      if (match.index > lastIndex) {
        tokens.push(<span key={lastIndex}>{line.slice(lastIndex, match.index)}</span>)
      }
      const m = match[0]
      if (match[1]) {
        tokens.push(
          <span key={match.index} className="text-purple-400 font-semibold">
            {m}
          </span>,
        )
      } else if (match[2]) {
        tokens.push(
          <span key={match.index} className="text-amber-300">
            {m}
          </span>,
        )
      } else if (
        m.startsWith('"') ||
        m.startsWith("'") ||
        m.startsWith('f"') ||
        m.startsWith("f'")
      ) {
        tokens.push(
          <span key={match.index} className="text-emerald-400">
            {m}
          </span>,
        )
      } else if (m.startsWith('http')) {
        tokens.push(
          <span key={match.index} className="text-sky-400 underline decoration-sky-400/30">
            {m}
          </span>,
        )
      } else if (match[4]) {
        tokens.push(
          <span key={match.index} className="text-amber-200">
            {m}
          </span>,
        )
      } else {
        tokens.push(<span key={match.index}>{m}</span>)
      }
      lastIndex = match.index + m.length
    }
    if (lastIndex < line.length) {
      tokens.push(<span key={lastIndex}>{line.slice(lastIndex)}</span>)
    }
  }

  if (tokens.length === 0) tokens.push(<span key="empty">{line || '\u00A0'}</span>)
  return tokens
}

/** Typewriter effect for code lines */
function useCodeTypewriter(lines: string[], trigger: boolean) {
  const [currentLine, setCurrentLine] = useState(0)
  const [currentChar, setCurrentChar] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval>>(null)
  const [key, setKey] = useState(0)

  const reset = useCallback(() => {
    setCurrentLine(0)
    setCurrentChar(0)
    setKey((k) => k + 1)
  }, [])

  useEffect(() => {
    if (!trigger) {
      reset()
      return
    }

    // Check reduced motion
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (mq.matches) {
      setCurrentLine(lines.length)
      setCurrentChar(0)
      return
    }

    // Start typing
    const totalLines = lines.length
    let line = 0
    let char = 0

    intervalRef.current = setInterval(() => {
      if (line >= totalLines) {
        if (intervalRef.current) clearInterval(intervalRef.current)
        return
      }

      const lineLen = lines[line].length
      if (char >= lineLen) {
        // Move to next line
        line++
        char = 0
        setCurrentLine(line)
        setCurrentChar(0)
      } else {
        char++
        setCurrentChar(char)
      }
    }, 18) // Fast character speed for code

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [trigger, lines, key, reset])

  return { currentLine, currentChar, reset }
}

export function CodeSection() {
  const { ref, isVisible } = useScrollReveal()
  const [activeTab, setActiveTab] = useState(0)
  const lines = tabs[activeTab].code.split('\n')
  const { currentLine, currentChar, reset } = useCodeTypewriter(lines, isVisible)

  // Reset typewriter when switching tabs
  const handleTabSwitch = (i: number) => {
    setActiveTab(i)
    reset()
  }

  return (
    <section className="bg-gray-50 px-6 py-24 dark:bg-slate-900/30">
      <div ref={ref} className="mx-auto max-w-4xl">
        {/* Header */}
        <div
          className={`mb-12 text-center transition-all duration-700 ease-out ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'
          }`}
        >
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-indigo-500/80 dark:text-indigo-400/80">
            Three API calls
          </p>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl">
            Integrate in minutes
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-500 dark:text-slate-400">
            Create an agent, route through the gateway, and query the audit trail. That&apos;s it.
          </p>
        </div>

        {/* Code block */}
        <div
          className={`overflow-hidden rounded-xl border border-gray-200 bg-gray-900 shadow-xl transition-all duration-700 ease-out dark:border-slate-700 ${
            isVisible ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
          }`}
          style={{ transitionDelay: '200ms' }}
        >
          {/* Tab bar */}
          <div className="flex border-b border-gray-700">
            {tabs.map((tab, i) => (
              <button
                key={tab.label}
                onClick={() => handleTabSwitch(i)}
                className={`px-6 py-3 text-sm font-medium transition-colors ${
                  activeTab === i
                    ? 'border-b-2 border-indigo-400 bg-gray-800 text-indigo-400'
                    : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}

            {/* Decorative dots */}
            <div className="ml-auto flex items-center gap-1.5 pr-4">
              <div className="h-3 w-3 rounded-full bg-red-500/60" />
              <div className="h-3 w-3 rounded-full bg-amber-500/60" />
              <div className="h-3 w-3 rounded-full bg-emerald-500/60" />
            </div>
          </div>

          {/* Code content with typewriter */}
          <div className="overflow-x-auto p-6">
            <pre className="font-[JetBrains_Mono,monospace] text-[13px] leading-relaxed text-gray-300">
              {lines.map((line, i) => {
                const isTyped = i < currentLine
                const isTyping = i === currentLine
                const visible = isTyped || isTyping

                if (!visible)
                  return (
                    <div key={`${activeTab}-${i}`} className="h-[1.625em]">
                      {'\u00A0'}
                    </div>
                  )

                const displayLine = isTyping ? line.slice(0, currentChar) : line
                const showCursor = isTyping && currentLine < lines.length

                return (
                  <div key={`${activeTab}-${i}`} className="min-h-[1.625em]">
                    {tokenizeLine(displayLine, tabs[activeTab].lang)}
                    {showCursor && (
                      <span
                        className="inline-block w-[2px] bg-indigo-400"
                        style={{ height: '1em', animation: 'cursor-blink 1.06s step-end infinite' }}
                      />
                    )}
                  </div>
                )
              })}
            </pre>
          </div>
        </div>
      </div>
    </section>
  )
}
