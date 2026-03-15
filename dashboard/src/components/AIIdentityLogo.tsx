interface LogoProps {
  className?: string
  variant?: 'light' | 'dark' | 'primary'
}

// Logo Variation 5: Three Rectangles - Ultra minimalist bar chart style
export function AIIdentityLogo5({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2',
  }

  const fillColor = colors[variant]

  return (
    <svg viewBox="0 0 400 200" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      {/* Three rectangles - bar chart style with varying heights, centered */}
      <rect x="140" y="50" width="30" height="45" fill={fillColor} rx="2" />
      <rect x="180" y="20" width="30" height="75" fill={fillColor} rx="2" />
      <rect x="220" y="35" width="30" height="60" fill={fillColor} rx="2" />

      {/* Text: AI IDENTITY in Inter Bold, centered */}
      <text
        x="200"
        y="150"
        fill={fillColor}
        fontFamily="Inter, sans-serif"
        fontWeight="700"
        fontSize="48"
        letterSpacing="4"
        textAnchor="middle"
      >
        AI IDENTITY
      </text>
    </svg>
  )
}
