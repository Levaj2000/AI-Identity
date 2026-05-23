/**
 * AI Identity logo — shield + Ai mark.
 *
 * Variants:
 *   mark  — icon only (nav, favicon, compact spaces)
 *   full  — icon + "AI Identity" wordmark
 */

interface LogoProps {
  variant?: 'mark' | 'full'
  size?: number
  className?: string
}

export function Logo({ variant = 'full', size = 32, className = '' }: LogoProps) {
  const mark = (
    <svg
      width={size}
      height={Math.round(size * 1.1)}
      viewBox="0 0 200 220"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      className="shrink-0"
    >
      <defs>
        <linearGradient id="dash-shield" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3A86C8" />
          <stop offset="0.5" stopColor="#1F5694" />
          <stop offset="1" stopColor="#143E73" />
        </linearGradient>
        <linearGradient id="dash-letter" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2F7CC2" />
          <stop offset="0.6" stopColor="#1E5694" />
          <stop offset="1" stopColor="#10325F" />
        </linearGradient>
        <linearGradient id="dash-letter-bright" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#A8D4F2" />
          <stop offset="0.6" stopColor="#5BA0DC" />
          <stop offset="1" stopColor="#3A86C8" />
        </linearGradient>
      </defs>
      <path
        d="M30 22 C30 13 38 8 47 8 L153 8 C162 8 170 13 170 22 L170 110 C170 158 138 192 100 210 C62 192 30 158 30 110 Z M45 32 C45 27 49 24 54 24 L146 24 C151 24 155 27 155 32 L155 108 C155 150 124 178 100 191 C76 178 45 150 45 108 Z"
        fill="url(#dash-shield)"
        fillRule="evenodd"
      />
      <path
        d="M62 156 L88 60 L106 60 L132 156 L117 156 L110 130 L84 130 L77 156 Z M87 116 L107 116 L97 78 Z"
        fill="url(#dash-letter)"
        fillRule="evenodd"
      />
      <rect x="141" y="92" width="11" height="64" rx="1.5" fill="url(#dash-letter-bright)" />
      <circle cx="146.5" cy="80" r="6.5" fill="url(#dash-letter-bright)" />
    </svg>
  )

  if (variant === 'mark') {
    return <div className={className}>{mark}</div>
  }

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {mark}
      <span className="text-lg font-bold tracking-tight text-gray-900 dark:text-slate-100">
        AI Identity
      </span>
    </div>
  )
}
