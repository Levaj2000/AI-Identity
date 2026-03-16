import type { ReactNode } from 'react'

interface StatsCardProps {
  label: string
  value: number
  icon: ReactNode
  accent?: string
  glowColor?: string
}

export function StatsCard({
  label,
  value,
  icon,
  accent = 'text-[#F59E0B]',
  glowColor = 'rgba(245,158,11,0.05)',
}: StatsCardProps) {
  return (
    <div
      className="relative overflow-hidden rounded-xl border border-gray-200 bg-white p-6 transition-colors hover:border-gray-300 dark:border-[#F59E0B]/10 dark:bg-[#111113]/80 dark:backdrop-blur-xl dark:hover:border-[#F59E0B]/25"
      style={{
        boxShadow: `0 0 15px ${glowColor}`,
      }}
    >
      {/* Gradient overlay using accent color */}
      <div
        className="pointer-events-none absolute inset-0 hidden dark:block"
        style={{
          background: `linear-gradient(135deg, ${glowColor} 0%, transparent 60%)`,
        }}
      />
      <div className={`relative mb-3 ${accent} drop-shadow-sm`}>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-current/10">
          {icon}
        </div>
      </div>
      <p className="relative text-3xl font-bold text-gray-900 font-[JetBrains_Mono,monospace] dark:text-[#e4e4e7]">
        {value}
      </p>
      <p className="relative mt-1 text-sm text-gray-500 dark:text-[#a1a1aa]">{label}</p>
    </div>
  )
}
