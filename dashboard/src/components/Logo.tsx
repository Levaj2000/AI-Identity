/**
 * AI Identity logo — hexagonal shield mark with stylized key + agent core.
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
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0"
    >
      {/* Hexagonal shield outline */}
      <path
        d="M16 2L28.5 9.5V22.5L16 30L3.5 22.5V9.5L16 2Z"
        stroke="#4F46E5"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />

      {/* Inner hexagon — layered depth */}
      <path
        d="M16 7L24 11.5V20.5L16 25L8 20.5V11.5L16 7Z"
        stroke="#4F46E5"
        strokeWidth="0.8"
        strokeLinejoin="round"
        opacity="0.35"
      />

      {/* Key head — circle at top */}
      <circle cx="16" cy="11" r="2.5" stroke="#4F46E5" strokeWidth="1.4" />

      {/* Key shaft */}
      <line
        x1="16"
        y1="13.5"
        x2="16"
        y2="22"
        stroke="#4F46E5"
        strokeWidth="1.4"
        strokeLinecap="round"
      />

      {/* Key teeth */}
      <line
        x1="16"
        y1="18"
        x2="19.5"
        y2="18"
        stroke="#4F46E5"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <line
        x1="16"
        y1="21"
        x2="18.5"
        y2="21"
        stroke="#4F46E5"
        strokeWidth="1.4"
        strokeLinecap="round"
      />

      {/* Agent identity core — amber accent */}
      <circle cx="16" cy="11" r="1" fill="#F59E0B" />
    </svg>
  )

  if (variant === 'mark') {
    return <div className={className}>{mark}</div>
  }

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {mark}
      <span className="text-lg font-bold tracking-tight">
        <span className="text-indigo-500">AI</span>{' '}
        <span className="text-gray-900 dark:text-slate-100">Identity</span>
      </span>
    </div>
  )
}
