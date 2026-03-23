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
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl">
      <div className="mb-4 flex items-center gap-2">
        <svg
          className="h-5 w-5 text-[#F59E0B]"
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
        <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">Quick Start</h2>
      </div>

      <div className="relative">
        <pre className="overflow-x-auto rounded-lg bg-gray-100 p-4 font-mono text-sm dark:bg-[#0A0A0B]">
          <code>
            <span className="text-gray-700 dark:text-[#e4e4e7]">curl -X POST </span>
            <span className="text-[#F59E0B]">https://api.ai-identity.co/v1/agents</span>
            <span className="text-gray-700 dark:text-[#e4e4e7]"> \</span>
            {'\n'}
            <span className="text-gray-700 dark:text-[#e4e4e7]">{'  '}-H </span>
            <span className="text-[#F59E0B]">&quot;Authorization: Bearer aid_sk_...&quot;</span>
            <span className="text-gray-700 dark:text-[#e4e4e7]"> \</span>
            {'\n'}
            <span className="text-gray-700 dark:text-[#e4e4e7]">{'  '}-H </span>
            <span className="text-[#F59E0B]">&quot;Content-Type: application/json&quot;</span>
            <span className="text-gray-700 dark:text-[#e4e4e7]"> \</span>
            {'\n'}
            <span className="text-gray-700 dark:text-[#e4e4e7]">{'  '}-d </span>
            <span className="text-[#F59E0B]">{`'{"name": "my-agent"}'`}</span>
          </code>
        </pre>
        <button
          onClick={handleCopy}
          className="absolute right-2 top-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-[#2a2a2d] dark:bg-[#1a1a1d] dark:text-[#e4e4e7] dark:hover:bg-[#2a2a2d]"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Gateway URL */}
      <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-[#2a2a2d] dark:bg-[#1a1a1d]">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-[#71717a]">
          Gateway URL &mdash; point your agents here
        </p>
        <code className="text-sm font-[JetBrains_Mono,monospace] text-[#F59E0B]">
          {GATEWAY_URL}
        </code>
        <p className="mt-1.5 text-xs text-gray-500 dark:text-[#a1a1aa]">
          Swap your OpenAI base URL for this. Add your <code>aid_sk_</code> key as the{' '}
          <code className="text-[#F59E0B]">X-API-Key</code> header.
        </p>
      </div>

      <div className="mt-4 flex items-center gap-6 text-sm">
        <a
          href="https://ai-identity.co/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-500 transition-colors hover:text-[#F59E0B] dark:text-[#71717a] dark:hover:text-[#F59E0B]"
        >
          Documentation &rarr;
        </a>
        <a
          href="https://api.ai-identity.co/redoc"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-500 transition-colors hover:text-[#F59E0B] dark:text-[#71717a] dark:hover:text-[#F59E0B]"
        >
          API Reference &rarr;
        </a>
        <a
          href="https://github.com/Levaj2000/AI-Identity#python-sdk"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-500 transition-colors hover:text-[#F59E0B] dark:text-[#71717a] dark:hover:text-[#F59E0B]"
        >
          Python SDK &rarr;
        </a>
        <a
          href="https://github.com/Levaj2000/AI-Identity#examples"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-500 transition-colors hover:text-[#F59E0B] dark:text-[#71717a] dark:hover:text-[#F59E0B]"
        >
          Examples &rarr;
        </a>
      </div>
    </div>
  )
}
