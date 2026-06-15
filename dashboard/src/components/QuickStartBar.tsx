import { useState } from 'react'
import { GATEWAY_URL } from '../config/api'

const curlCommand = `curl -X POST https://api.ai-identity.co/v1/agents \\
  -H "Authorization: Bearer aid_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-agent"}'`

export function QuickStartBar() {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(curlCommand).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <div className="mb-4 flex items-center gap-2">
        <svg
          className="h-5 w-5 text-brand"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <h2 className="text-lg font-semibold text-ink">Quick Start</h2>
      </div>

      <div className="relative">
        <pre className="overflow-x-auto rounded-lg bg-inset p-4 font-mono text-sm">
          <code>
            <span className="text-muted">curl -X POST </span>
            <span className="text-brand">https://api.ai-identity.co/v1/agents</span>
            <span className="text-muted"> \</span>
            {'\n'}
            <span className="text-muted">{'  '}-H </span>
            <span className="text-brand">&quot;Authorization: Bearer aid_sk_...&quot;</span>
            <span className="text-muted"> \</span>
            {'\n'}
            <span className="text-muted">{'  '}-H </span>
            <span className="text-brand">&quot;Content-Type: application/json&quot;</span>
            <span className="text-muted"> \</span>
            {'\n'}
            <span className="text-muted">{'  '}-d </span>
            <span className="text-brand">{`'{"name": "my-agent"}'`}</span>
          </code>
        </pre>
        <button
          onClick={handleCopy}
          className="absolute right-2 top-2 rounded-md border border-line-strong bg-surface px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-elevated"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Gateway URL */}
      <div className="mt-4 rounded-lg border border-line bg-inset p-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-subtle">
          Gateway URL &mdash; point your agents here
        </p>
        <code className="text-sm font-[JetBrains_Mono,monospace] text-brand">{GATEWAY_URL}</code>
        <p className="mt-1.5 text-xs text-muted">
          Swap your OpenAI base URL for this. Add your <code>aid_sk_</code> key as the{' '}
          <code className="text-brand">X-API-Key</code> header.
        </p>
      </div>

      <div className="mt-4 flex items-center gap-6 text-sm">
        <a
          href="https://ai-identity.co/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="text-subtle transition-colors hover:text-brand"
        >
          Documentation &rarr;
        </a>
        <a
          href="https://api.ai-identity.co/redoc"
          target="_blank"
          rel="noopener noreferrer"
          className="text-subtle transition-colors hover:text-brand"
        >
          API Reference &rarr;
        </a>
        <a
          href="https://github.com/Levaj2000/AI-Identity#python-sdk"
          target="_blank"
          rel="noopener noreferrer"
          className="text-subtle transition-colors hover:text-brand"
        >
          Python SDK &rarr;
        </a>
        <a
          href="https://github.com/Levaj2000/AI-Identity#examples"
          target="_blank"
          rel="noopener noreferrer"
          className="text-subtle transition-colors hover:text-brand"
        >
          Examples &rarr;
        </a>
      </div>
    </div>
  )
}
