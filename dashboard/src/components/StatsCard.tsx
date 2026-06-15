import type { ReactNode } from 'react'

interface StatsCardProps {
  label: string
  value: number
  icon: ReactNode
  accent?: string
}

export function StatsCard({ label, value, icon, accent = 'text-brand' }: StatsCardProps) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-line bg-surface p-6 transition-colors hover:border-line-strong">
      <div className={`relative mb-3 ${accent} drop-shadow-sm`}>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-current/10">
          {icon}
        </div>
      </div>
      <p className="relative font-[JetBrains_Mono,monospace] text-3xl font-bold text-ink">
        {value}
      </p>
      <p className="relative mt-1 text-sm text-muted">{label}</p>
    </div>
  )
}
