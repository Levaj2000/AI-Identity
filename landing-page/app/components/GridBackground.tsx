interface GridBackgroundProps {
  variant?: 'dots' | 'lines' | 'circuit';
  opacity?: number;
  className?: string;
}

export function GridBackground({ variant = 'dots', opacity = 0.15, className = '' }: GridBackgroundProps) {
  if (variant === 'dots') {
    return (
      <div className={`absolute inset-0 pointer-events-none ${className}`} style={{ opacity }}>
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="dot-grid" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" fill="#00FFC2" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#dot-grid)" />
        </svg>
      </div>
    );
  }

  if (variant === 'lines') {
    return (
      <div className={`absolute inset-0 pointer-events-none ${className}`} style={{ opacity }}>
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="line-grid" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#00FFC2" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#line-grid)" />
        </svg>
      </div>
    );
  }

  // Circuit variant - more technical looking
  return (
    <div className={`absolute inset-0 pointer-events-none ${className}`} style={{ opacity }}>
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="circuit-grid" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
            {/* Grid lines */}
            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#00FFC2" strokeWidth="0.5" opacity="0.3" />

            {/* Circuit nodes at intersections */}
            <circle cx="0" cy="0" r="1.5" fill="#00FFC2" opacity="0.6" />
            <circle cx="50" cy="0" r="1" fill="#00FFC2" opacity="0.4" />
            <circle cx="0" cy="50" r="1" fill="#00FFC2" opacity="0.4" />

            {/* Small connecting lines for circuit feel */}
            <line x1="0" y1="0" x2="10" y2="0" stroke="#00FFC2" strokeWidth="1" opacity="0.2" />
            <line x1="0" y1="0" x2="0" y2="10" stroke="#00FFC2" strokeWidth="1" opacity="0.2" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#circuit-grid)" />
      </svg>
    </div>
  );
}

// Animated grid variant with subtle pulse effect
export function AnimatedGridBackground({
  opacity = 0.1,
  className = '',
  animationType = 'pulse'
}: {
  opacity?: number;
  className?: string;
  animationType?: 'pulse' | 'wave';
}) {
  return (
    <div className={`absolute inset-0 pointer-events-none overflow-hidden ${className}`}>
      <style>
        {`
          @keyframes grid-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
          }
        `}
      </style>

      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0, 255, 194, ${opacity}) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 194, ${opacity}) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
          animation: 'grid-pulse 8s ease-in-out infinite'
        }}
      />

      {/* Add some random glowing dots */}
      <div className="absolute inset-0">
        <div className="absolute top-[15%] left-[20%] w-1 h-1 rounded-full bg-[#00FFC2] opacity-60 animate-pulse" style={{ animationDuration: '3s' }} />
        <div className="absolute top-[45%] left-[60%] w-1 h-1 rounded-full bg-[#00FFC2] opacity-40 animate-pulse" style={{ animationDuration: '4s' }} />
        <div className="absolute top-[70%] left-[35%] w-1 h-1 rounded-full bg-[#00FFC2] opacity-50 animate-pulse" style={{ animationDuration: '5s' }} />
        <div className="absolute top-[25%] left-[80%] w-1 h-1 rounded-full bg-[#00FFC2] opacity-45 animate-pulse" style={{ animationDuration: '3.5s' }} />
        <div className="absolute top-[85%] left-[15%] w-1 h-1 rounded-full bg-[#00FFC2] opacity-55 animate-pulse" style={{ animationDuration: '4.5s' }} />
      </div>
    </div>
  );
}
