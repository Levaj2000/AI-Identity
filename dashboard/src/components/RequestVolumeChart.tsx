import { useState, useEffect } from 'react'
import { apiFetch } from '../services/api/client'
import { useAuth } from '../hooks/useAuth'

interface DailyData {
  date: string
  total_requests: number
}

interface AggregationResponse {
  billing_period: {
    total_requests: number
    peak_daily_requests: number
    avg_daily_requests: number
  }
  daily: DailyData[]
}

export function RequestVolumeChart() {
  const { user } = useAuth()
  const [data, setData] = useState<DailyData[]>([])
  const [total, setTotal] = useState(0)
  const [peak, setPeak] = useState(0)
  const [avg, setAvg] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  useEffect(() => {
    if (!user) return
    apiFetch<AggregationResponse>('/api/v1/usage/aggregation')
      .then((res) => {
        // Show last 7 days of data
        const last7 = res.daily.slice(-7)
        setData(last7)
        setTotal(res.billing_period.total_requests)
        setPeak(res.billing_period.peak_daily_requests)
        setAvg(Math.round(res.billing_period.avg_daily_requests))
      })
      .catch(() => {
        // fail silently — chart just stays empty
      })
      .finally(() => setIsLoading(false))
  }, [user])

  if (isLoading) {
    return <div className="h-80 animate-pulse rounded-xl bg-gray-200 dark:bg-[#10131C]" />
  }

  const dayLabels = data.map((d) => {
    const date = new Date(d.date + 'T00:00:00')
    return date.toLocaleDateString('en-US', { weekday: 'short' })
  })
  const values = data.map((d) => d.total_requests)
  const maxVal = Math.max(...values, 1) * 1.1

  const padding = { top: 20, right: 20, bottom: 30, left: 20 }
  const chartHeight = 200
  const chartWidth = 500
  const innerWidth = chartWidth - padding.left - padding.right
  const innerHeight = chartHeight - padding.top - padding.bottom

  const points = values.map((v, i) => ({
    x: padding.left + (i / Math.max(values.length - 1, 1)) * innerWidth,
    y: padding.top + innerHeight - (v / maxVal) * innerHeight,
  }))

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  const areaPath = `${linePath} L${points[points.length - 1].x},${padding.top + innerHeight} L${points[0].x},${padding.top + innerHeight} Z`

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-[#A6DAFF]/10 dark:bg-[#10131C]/80 dark:backdrop-blur-xl">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
            Request Volume
          </h2>
          <p className="text-sm text-gray-500 dark:text-[#71717a]">Last 7 days</p>
        </div>
        <span className="text-2xl font-bold text-[#A6DAFF]">{total.toLocaleString()}</span>
      </div>

      {total === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-sm text-gray-500 dark:text-[#71717a]">
          No request data yet — volume will appear as your agents process requests.
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full"
          style={{ height: 200 }}
        >
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#A6DAFF" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#A6DAFF" stopOpacity="0" />
            </linearGradient>
          </defs>

          <path d={areaPath} fill="url(#areaGradient)" />
          <path
            d={linePath}
            fill="none"
            stroke="#A6DAFF"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {points.map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y}
                r={hoveredIndex === i ? 5 : 3.5}
                fill="#A6DAFF"
                stroke="#04070D"
                strokeWidth="2"
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
              <circle
                cx={p.x}
                cy={p.y}
                r={16}
                fill="transparent"
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
              {hoveredIndex === i && (
                <g>
                  <rect
                    x={p.x - 30}
                    y={p.y - 30}
                    width="60"
                    height="22"
                    rx="4"
                    fill="#1a1a1d"
                    stroke="#A6DAFF"
                    strokeWidth="0.5"
                  />
                  <text
                    x={p.x}
                    y={p.y - 15}
                    textAnchor="middle"
                    fill="#A6DAFF"
                    fontSize="12"
                    fontWeight="600"
                  >
                    {values[i].toLocaleString()}
                  </text>
                </g>
              )}
              <text
                x={p.x}
                y={padding.top + innerHeight + 18}
                textAnchor="middle"
                fill="#71717a"
                fontSize="11"
              >
                {dayLabels[i]}
              </text>
            </g>
          ))}
        </svg>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4 text-sm dark:border-[#1a1a1d]">
        <span className="text-gray-500 dark:text-[#71717a]">
          Peak:{' '}
          <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
            {peak.toLocaleString()}
          </span>
        </span>
        <span className="text-gray-500 dark:text-[#71717a]">
          Avg:{' '}
          <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
            {avg.toLocaleString()}
          </span>
        </span>
        <span className="text-gray-500 dark:text-[#71717a]">
          Total:{' '}
          <span className="font-medium text-gray-900 dark:text-[#e4e4e7]">
            {total.toLocaleString()}
          </span>
        </span>
      </div>
    </div>
  )
}
