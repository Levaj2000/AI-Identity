import type { ReactNode } from 'react'

interface StatsCardProps {
  label: string
  value: number
  icon: ReactNode
  accent?: string
}

export function StatsCard({ label, value, icon, accent = 'text-indigo-500' }: StatsCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 transition-colors hover:border-slate-700">
      <div className={`mb-3 ${accent}`}>{icon}</div>
      <p className="text-3xl font-bold text-slate-100 font-[JetBrains_Mono,monospace]">{value}</p>
      <p className="mt-1 text-sm text-slate-400">{label}</p>
    </div>
  )
}
