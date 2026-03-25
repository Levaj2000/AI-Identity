/**
 * anomalyDetection — flag suspicious patterns in audit log entries.
 *
 * Detects latency spikes, cost outliers, and deny clusters
 * to surface potential incidents in the forensics UI.
 */

import type { AuditLogEntry } from '../../types/api'

export type AnomalyType = 'latency_spike' | 'cost_outlier' | 'deny_cluster'

export interface AnomalyFlag {
  type: AnomalyType
  detail: string
}

/**
 * Scan entries for anomalous patterns and return a map keyed by entry ID.
 *
 * 1. Latency spikes — group by agent_id, compute average latency,
 *    flag any entry > 2x the agent's average.
 * 2. Cost outliers — same approach with cost_estimate_usd.
 * 3. Deny clusters — sort by created_at, for each deny, count
 *    denies within a 60-second window and flag if 3+.
 */
export function detectAnomalies(entries: AuditLogEntry[]): Map<number, AnomalyFlag[]> {
  const result = new Map<number, AnomalyFlag[]>()

  const push = (id: number, flag: AnomalyFlag) => {
    const existing = result.get(id)
    if (existing) {
      existing.push(flag)
    } else {
      result.set(id, [flag])
    }
  }

  // ── 1. Latency spikes ────────────────────────────────────────
  const latencyByAgent = new Map<string, { sum: number; count: number }>()
  for (const e of entries) {
    if (e.latency_ms == null) continue
    const agg = latencyByAgent.get(e.agent_id)
    if (agg) {
      agg.sum += e.latency_ms
      agg.count += 1
    } else {
      latencyByAgent.set(e.agent_id, { sum: e.latency_ms, count: 1 })
    }
  }

  for (const e of entries) {
    if (e.latency_ms == null) continue
    const agg = latencyByAgent.get(e.agent_id)
    if (!agg || agg.count < 2) continue
    const avg = agg.sum / agg.count
    if (avg > 0 && e.latency_ms > avg * 2) {
      push(e.id, {
        type: 'latency_spike',
        detail: `${e.latency_ms}ms vs ${Math.round(avg)}ms avg`,
      })
    }
  }

  // ── 2. Cost outliers ─────────────────────────────────────────
  const costByAgent = new Map<string, { sum: number; count: number }>()
  for (const e of entries) {
    if (e.cost_estimate_usd == null) continue
    const agg = costByAgent.get(e.agent_id)
    if (agg) {
      agg.sum += e.cost_estimate_usd
      agg.count += 1
    } else {
      costByAgent.set(e.agent_id, { sum: e.cost_estimate_usd, count: 1 })
    }
  }

  for (const e of entries) {
    if (e.cost_estimate_usd == null) continue
    const agg = costByAgent.get(e.agent_id)
    if (!agg || agg.count < 2) continue
    const avg = agg.sum / agg.count
    if (avg > 0 && e.cost_estimate_usd > avg * 2) {
      push(e.id, {
        type: 'cost_outlier',
        detail: `$${e.cost_estimate_usd.toFixed(4)} vs $${avg.toFixed(4)} avg`,
      })
    }
  }

  // ── 3. Deny clusters ─────────────────────────────────────────
  const denies = entries
    .filter((e) => e.decision === 'deny' || e.decision === 'denied')
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())

  for (let i = 0; i < denies.length; i++) {
    const t = new Date(denies[i].created_at).getTime()
    let windowCount = 0
    for (let j = 0; j < denies.length; j++) {
      const tj = new Date(denies[j].created_at).getTime()
      if (Math.abs(tj - t) <= 60_000) windowCount++
    }
    if (windowCount >= 3) {
      push(denies[i].id, {
        type: 'deny_cluster',
        detail: `${windowCount} denies within 60s`,
      })
    }
  }

  return result
}
