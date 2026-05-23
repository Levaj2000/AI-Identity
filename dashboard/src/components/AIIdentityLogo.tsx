interface LogoProps {
  className?: string
  variant?: 'light' | 'dark' | 'primary'
}

/**
 * AI Identity wordmark — shield + Ai mark followed by "AI IDENTITY".
 * Kept under the AIIdentityLogo5 name so existing imports (Sidebar) keep working.
 */
export function AIIdentityLogo5({ className = '', variant = 'primary' }: LogoProps) {
  // Wordmark color: white on dark UI, ink on light, accent blue for primary placement
  const textColor = {
    light: '#FFFFFF',
    dark: '#04070D',
    primary: '#E6EDF7',
  }[variant]

  return (
    <svg viewBox="0 0 720 220" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <defs>
        <linearGradient id="aiid5-shield" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5BA0DC" />
          <stop offset="0.5" stopColor="#3A86C8" />
          <stop offset="1" stopColor="#1F5694" />
        </linearGradient>
        <linearGradient id="aiid5-letter" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7CB6E2" />
          <stop offset="0.6" stopColor="#3A86C8" />
          <stop offset="1" stopColor="#1F5694" />
        </linearGradient>
      </defs>

      {/* Shield mark */}
      <path
        d="M30 22 C30 13 38 8 47 8 L153 8 C162 8 170 13 170 22 L170 110 C170 158 138 192 100 210 C62 192 30 158 30 110 Z M45 32 C45 27 49 24 54 24 L146 24 C151 24 155 27 155 32 L155 108 C155 150 124 178 100 191 C76 178 45 150 45 108 Z"
        fill="url(#aiid5-shield)"
        fillRule="evenodd"
      />
      <path
        d="M62 156 L90 60 L110 60 L138 156 L122 156 L115 130 L85 130 L78 156 Z M89 116 L111 116 L100 78 Z"
        fill="url(#aiid5-letter)"
        fillRule="evenodd"
      />
      <rect x="146" y="92" width="12" height="64" rx="1.5" fill="url(#aiid5-letter)" />
      <circle cx="152" cy="80" r="6.5" fill="url(#aiid5-letter)" />

      {/* Wordmark */}
      <text
        x="210"
        y="140"
        fill={textColor}
        fontFamily="Inter, Helvetica Neue, Helvetica, Arial, sans-serif"
        fontWeight="700"
        fontSize="80"
        letterSpacing="2"
      >
        AI IDENTITY
      </text>
    </svg>
  )
}
