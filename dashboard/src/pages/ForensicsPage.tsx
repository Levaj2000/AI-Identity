/**
 * ForensicsPage — AI Forensics dashboard for incident investigation.
 *
 * Timeline view, stats, filtering, incident reconstruction,
 * and exportable forensics reports with chain-of-custody verification.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router'
import type {
  Agent,
  AuditLogEntry,
  AuditStatsResponse,
  AuditSummaryResponse,
  AuditReconstructResponse,
  ForensicsFilterParams,
} from '../types/api'
import { apiFetch } from '../services/api/client'
import {
  fetchAuditLogs,
  fetchAuditStats,
  fetchAuditReconstruct,
  fetchAuditSummary,
  fetchForensicsReport,
  downloadOcsf,
  downloadVerifyBundle,
  verifyAuditChain,
} from '../services/api/forensics'
import { CaseFileVerifyPanel } from '../components/forensics/CaseFileVerifyPanel'
import { InclusionProofPanel } from '../components/forensics/InclusionProofPanel'
import { ExportMenu } from '../components/forensics/ExportMenu'
import { ForensicsTimeline } from '../components/forensics/ForensicsTimeline'
import { IncidentReconstructModal } from '../components/forensics/IncidentReconstructModal'
import { EventDetailDrawer } from '../components/forensics/EventDetailDrawer'
import { AISummaryPanel } from '../components/forensics/AISummaryPanel'
import { AILensMenu } from '../components/forensics/AILensMenu'
import {
  ForensicsAlertBanner,
  type ForensicsAlert,
} from '../components/forensics/ForensicsAlertBanner'
import { FilterSummaryBar, type FilterChip } from '../components/forensics/FilterSummaryBar'
import { detectAnomalies } from '../components/forensics/anomalyDetection'
import { HashChainView } from '../components/forensics/HashChainView'

// ── Helpers ──────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function decisionBadge(d: string) {
  if (d === 'allow' || d === 'allowed') return 'bg-success-soft text-success border-success'
  if (d === 'deny' || d === 'denied') return 'bg-danger-soft text-danger border-danger'
  return 'bg-warning-soft text-warning border-warning'
}

/** Convert a Date to a datetime-local input value in *local* time. Used by
 *  the alert drill-down so the narrowed window actually brackets the anchor.
 *  (defaultStartDate/defaultEndDate use UTC wall-clock — a pre-existing quirk
 *  we don't touch here.) */
function toLocalDatetimeInput(d: Date): string {
  const off = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - off).toISOString().slice(0, 16)
}

/** Compact label for a datetime-local value (e.g. "Apr 9, 2:39 AM"). */
function shortDateLabel(local: string): string {
  if (!local) return '—'
  return new Date(local).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Default to last 7 days. */
function defaultStartDate(): string {
  const d = new Date()
  d.setDate(d.getDate() - 7)
  return d.toISOString().slice(0, 16)
}

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 16)
}

// ── Component ────────────────────────────────────────────────────

export function ForensicsPage() {
  // Agents list
  const [agents, setAgents] = useState<Agent[]>([])

  // Filters
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [startDate, setStartDate] = useState(defaultStartDate())
  const [endDate, setEndDate] = useState(defaultEndDate())

  // Initial (default) window, frozen once at mount. The drill-down narrows the
  // window; comparing against this freeze lets the summary bar show a clearable
  // "window" chip only when the analyst has moved off the default 7-day view.
  const defaultWindow = useRef({ start: defaultStartDate(), end: defaultEndDate() })
  const resetWindow = useCallback(() => {
    setStartDate(defaultWindow.current.start)
    setEndDate(defaultWindow.current.end)
    setOffset(0)
  }, [])
  const [filterDecision, setFilterDecision] = useState<string>('')
  const [filterEndpoint, setFilterEndpoint] = useState<string>('')
  const [filterActionType, setFilterActionType] = useState<string>('')
  const [filterModel, setFilterModel] = useState<string>('')
  const [filterCostMin, setFilterCostMin] = useState<string>('')
  const [filterCostMax, setFilterCostMax] = useState<string>('')

  // Data
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<AuditStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const limit = 50

  // View mode
  const [viewMode, setViewMode] = useState<'timeline' | 'table'>('timeline')

  // Chain verification (cryptographic tamper-evidence check)
  const [chainValid, setChainValid] = useState<boolean | null>(null)
  const [chainMessage, setChainMessage] = useState<string>('')
  const [chainEntriesVerified, setChainEntriesVerified] = useState<number>(0)
  const [chainFirstBrokenId, setChainFirstBrokenId] = useState<number | null>(null)

  // Incident reconstruction
  const [reconstructData, setReconstructData] = useState<AuditReconstructResponse | null>(null)
  const [reconstructing, setReconstructing] = useState(false)

  // AI Summary (Perplexity)
  const [summaryData, setSummaryData] = useState<AuditSummaryResponse | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [showSummaryPanel, setShowSummaryPanel] = useState(false)

  // Deep-linked agent_id (e.g. from Shadow Agents page) — may not be a registered agent
  const [deepLinkedAgentId, setDeepLinkedAgentId] = useState<string | null>(null)

  // Hydrate from URL search params
  const [searchParams] = useSearchParams()
  const hydrated = useRef(false)
  useEffect(() => {
    if (hydrated.current) return
    hydrated.current = true
    const qAgent = searchParams.get('agent_id')
    const qStart = searchParams.get('start')
    const qEnd = searchParams.get('end')
    if (qAgent) {
      // Check if this agent_id is a registered agent (will be resolved after agents load)
      setDeepLinkedAgentId(qAgent)
    }
    if (qStart) setStartDate(qStart)
    if (qEnd) setEndDate(qEnd)
  }, [searchParams])

  // Once agents load, resolve deep-linked agent: if registered, use the dropdown; otherwise keep as direct filter
  useEffect(() => {
    if (!deepLinkedAgentId) return
    const isRegistered = agents.some((a) => a.id === deepLinkedAgentId)
    if (isRegistered) {
      setSelectedAgent(deepLinkedAgentId)
      setDeepLinkedAgentId(null)
    }
  }, [agents, deepLinkedAgentId])

  // The effective agent_id filter: dropdown selection OR deep-linked unregistered agent
  const effectiveAgentId = selectedAgent || deepLinkedAgentId || ''

  // For exports: auto-resolve to the sole agent when "All Agents" is selected and there's exactly one
  const resolvedAgentId = effectiveAgentId || (agents.length === 1 ? agents[0].id : '')

  // Event detail drawer
  const [selectedEvent, setSelectedEvent] = useState<AuditLogEntry | null>(null)

  // ── Fetch agents ──────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false
    apiFetch<{ items: Agent[] }>('/api/v1/agents?limit=100')
      .then((data) => {
        if (!cancelled) setAgents(data.items)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  // ── Fetch audit entries ───────────────────────────────────────

  const loadEntries = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number | undefined> = {
        limit,
        offset,
      }
      if (effectiveAgentId) params.agent_id = effectiveAgentId
      if (filterDecision) params.decision = filterDecision
      if (startDate) params.start_date = new Date(startDate).toISOString()
      if (endDate) params.end_date = new Date(endDate).toISOString()
      if (filterEndpoint) params.endpoint = filterEndpoint
      if (filterActionType) params.action_type = filterActionType
      if (filterModel) params.model = filterModel
      if (filterCostMin) params.cost_min = parseFloat(filterCostMin)
      if (filterCostMax) params.cost_max = parseFloat(filterCostMax)

      const data = await fetchAuditLogs(params as ForensicsFilterParams)
      setEntries(data.items)
      setTotal(data.total)
    } catch {
      setEntries([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [
    effectiveAgentId,
    filterDecision,
    startDate,
    endDate,
    filterEndpoint,
    filterActionType,
    filterModel,
    filterCostMin,
    filterCostMax,
    offset,
  ])

  useEffect(() => {
    loadEntries()
  }, [loadEntries])

  // ── Fetch stats ───────────────────────────────────────────────

  useEffect(() => {
    const params: Record<string, string | undefined> = {}
    if (effectiveAgentId) params.agent_id = effectiveAgentId
    if (startDate) params.start_date = new Date(startDate).toISOString()
    if (endDate) params.end_date = new Date(endDate).toISOString()

    fetchAuditStats(params)
      .then(setStats)
      .catch(() => setStats(null))
  }, [effectiveAgentId, startDate, endDate])

  // ── Verify chain (on-demand only — expensive call) ────────────

  const [chainVerifying, setChainVerifying] = useState(false)

  const handleVerifyChain = useCallback(async () => {
    setChainVerifying(true)
    try {
      const r = await verifyAuditChain(effectiveAgentId || undefined)
      setChainValid(r.valid)
      setChainMessage(r.message)
      setChainEntriesVerified(r.entries_verified)
      setChainFirstBrokenId(r.first_broken_id)
    } catch {
      setChainValid(null)
      setChainMessage('')
      setChainEntriesVerified(0)
      setChainFirstBrokenId(null)
    } finally {
      setChainVerifying(false)
    }
  }, [effectiveAgentId])

  // Reset chain status when agent changes
  useEffect(() => {
    setChainValid(null)
    setChainMessage('')
    setChainEntriesVerified(0)
    setChainFirstBrokenId(null)
  }, [effectiveAgentId])

  // ── Incident reconstruction ───────────────────────────────────

  const handleReconstruct = async () => {
    if (!effectiveAgentId) return
    setReconstructing(true)
    try {
      const data = await fetchAuditReconstruct({
        agent_id: effectiveAgentId,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      })
      setReconstructData(data)
    } catch {
      alert('Failed to reconstruct incident')
    } finally {
      setReconstructing(false)
    }
  }

  // ── Export ────────────────────────────────────────────────────

  const exportJSON = async () => {
    const agentId = resolvedAgentId
    if (!agentId) {
      alert('Please select a specific agent to export a report')
      return
    }
    try {
      const report = await fetchForensicsReport({
        agent_id: agentId,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      })
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `forensics-report-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // Fall back to local state if API call fails
      const report = reconstructData || { events: entries, stats }
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `forensics-report-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const exportOcsf = async () => {
    const agentId = resolvedAgentId
    if (!agentId) {
      alert('Please select a specific agent to export OCSF events')
      return
    }
    try {
      await downloadOcsf({
        agent_id: agentId,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      })
    } catch {
      alert('OCSF export failed')
    }
  }

  const exportBundle = async () => {
    const agentId = resolvedAgentId
    if (!agentId) {
      alert('Please select a specific agent to download the verification bundle')
      return
    }
    try {
      await downloadVerifyBundle({
        agent_id: agentId,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      })
    } catch {
      alert('Verification bundle download failed')
    }
  }

  const exportCSV = () => {
    const rows = [
      [
        'id',
        'agent_id',
        'endpoint',
        'method',
        'decision',
        'cost_usd',
        'latency_ms',
        'created_at',
        'entry_hash',
      ].join(','),
      ...entries.map((e) =>
        [
          e.id,
          e.agent_id,
          e.endpoint,
          e.method,
          e.decision,
          e.cost_estimate_usd ?? '',
          e.latency_ms ?? '',
          e.created_at,
          e.entry_hash,
        ].join(','),
      ),
    ].join('\n')
    const blob = new Blob([rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `forensics-export-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── AI Summary handler ───────────────────────────────────────

  /** Track what the active summary is scoped to, for the panel header. */
  const [summaryScope, setSummaryScope] = useState<string>('')

  /** Build the request body that mirrors the currently visible filter set. */
  const buildVisibleScopeParams = useCallback((): Record<string, unknown> => {
    const params: Record<string, unknown> = { max_events: 200 }
    const effectiveAgentId = deepLinkedAgentId || selectedAgent
    if (effectiveAgentId) params.agent_id = effectiveAgentId
    if (startDate) params.start_date = new Date(startDate).toISOString()
    if (endDate) params.end_date = new Date(endDate).toISOString()
    if (filterDecision) params.decision = filterDecision
    if (filterEndpoint) params.endpoint = filterEndpoint
    if (filterActionType) params.action_type = filterActionType
    if (filterModel) params.model = filterModel
    if (filterCostMin) params.cost_min = parseFloat(filterCostMin)
    if (filterCostMax) params.cost_max = parseFloat(filterCostMax)
    return params
  }, [
    deepLinkedAgentId,
    selectedAgent,
    startDate,
    endDate,
    filterDecision,
    filterEndpoint,
    filterActionType,
    filterModel,
    filterCostMin,
    filterCostMax,
  ])

  // Client-side cache for /audit/summarize results, keyed by JSON-stringified
  // params. Avoids re-hitting the LLM (and its rate limit) when the analyst
  // toggles between lenses on the same window. Cleared on full page reload.
  const summaryCacheRef = useRef<Map<string, AuditSummaryResponse>>(new Map())

  // Track the most recent summary call so the Regenerate button can re-run
  // the exact same lens with force=true (bypassing cache).
  const lastSummaryRequestRef = useRef<{
    params: Record<string, unknown>
    scopeLabel: string
  } | null>(null)

  /** Run a summary call with the given params and scope label.
   *
   * Caches results by params. Pass `{ force: true }` to bypass the cache —
   * used by the Regenerate button.
   */
  const runSummary = useCallback(
    async (params: Record<string, unknown>, scopeLabel: string, opts?: { force?: boolean }) => {
      setSummaryScope(scopeLabel)
      setShowSummaryPanel(true)
      lastSummaryRequestRef.current = { params, scopeLabel }

      const cacheKey = JSON.stringify(params)
      if (!opts?.force) {
        const cached = summaryCacheRef.current.get(cacheKey)
        if (cached) {
          setSummaryData(cached)
          setSummaryError(null)
          setSummaryLoading(false)
          return
        }
      }

      setSummaryLoading(true)
      setSummaryError(null)
      try {
        const data = await fetchAuditSummary(params)
        summaryCacheRef.current.set(cacheKey, data)
        setSummaryData(data)
      } catch (err: unknown) {
        const apiErr = err as { status?: number; message?: string }
        if (apiErr.status === 403) {
          setSummaryError('AI Summaries require a Pro or higher plan.')
        } else if (apiErr.status === 429) {
          setSummaryError('Rate limit reached. Please try again later.')
        } else {
          setSummaryError('Failed to generate summary. Please try again.')
        }
      } finally {
        setSummaryLoading(false)
      }
    },
    [],
  )

  /** Regenerate the most recent summary, bypassing the cache. */
  const handleRegenerate = useCallback(() => {
    const last = lastSummaryRequestRef.current
    if (!last) {
      // Nothing to regenerate — fall back to the broad visible-scope summary.
      const params = buildVisibleScopeParams()
      const scopeLabel = `Analyzing ${entries.length} visible event${entries.length === 1 ? '' : 's'}`
      return runSummary(params, scopeLabel, { force: true })
    }
    return runSummary(last.params, last.scopeLabel, { force: true })
  }, [runSummary, buildVisibleScopeParams, entries.length])

  const handleSummarize = useCallback(() => {
    const params = buildVisibleScopeParams()
    const scopeLabel = `Analyzing ${entries.length} visible event${entries.length === 1 ? '' : 's'}`
    return runSummary(params, scopeLabel)
  }, [buildVisibleScopeParams, runSummary, entries.length])

  /** Explain a specific anomaly (deny cluster, latency spike, cost outlier). */
  const handleExplainAnomaly = useCallback(
    (anchor: AuditLogEntry, anomalyType: 'deny_cluster' | 'latency_spike' | 'cost_outlier') => {
      const anchorTime = new Date(anchor.created_at).getTime()
      let eventIds: number[]
      let scopeLabel: string
      let focusHint: string

      if (anomalyType === 'deny_cluster') {
        // Gather all denies within ±60s of the anchor
        const window = entries.filter((e) => {
          const isDeny = e.decision === 'deny' || e.decision === 'denied'
          if (!isDeny) return false
          return Math.abs(new Date(e.created_at).getTime() - anchorTime) <= 60_000
        })
        eventIds = window.map((e) => e.id)
        scopeLabel = `Deny cluster — ${window.length} denies within 60s of ${new Date(anchor.created_at).toLocaleTimeString()}`
        focusHint = `Deny cluster of ${window.length} requests within 60s. Identify the root cause from deny_reason, endpoints, and agents involved. Recommend remediation.`
      } else if (anomalyType === 'latency_spike') {
        eventIds = [anchor.id]
        scopeLabel = `Latency spike — ${anchor.method} ${anchor.endpoint} (${anchor.latency_ms}ms)`
        focusHint = `Latency spike. Explain why this request was slower than the agent's baseline and what to investigate.`
      } else {
        eventIds = [anchor.id]
        scopeLabel = `Cost outlier — ${anchor.method} ${anchor.endpoint} ($${anchor.cost_estimate_usd?.toFixed(4)})`
        focusHint = `Cost outlier. Explain why this request cost more than the agent's baseline and whether this looks operational or anomalous.`
      }

      const params: Record<string, unknown> = {
        event_ids: eventIds,
        max_events: Math.max(eventIds.length, 1),
        focus_hint: focusHint,
      }
      return runSummary(params, scopeLabel)
    },
    [entries, runSummary],
  )

  /** Drill into a deny cluster: narrow the table to the incident window, flip
   *  the decision filter to denied, and pin the AI brief. The brief itself
   *  re-gathers the exact ±60s denies from `entries`, so the window narrowing
   *  here is purely the visual half of the drill-down. */
  const handleInvestigateCluster = useCallback(
    (anchor: AuditLogEntry) => {
      const t = new Date(anchor.created_at).getTime()
      const MARGIN = 120_000 // ±2 min: cluster spans 60s; show a little context
      setStartDate(toLocalDatetimeInput(new Date(t - MARGIN)))
      setEndDate(toLocalDatetimeInput(new Date(t + MARGIN)))
      setFilterDecision('denied')
      setOffset(0)
      handleExplainAnomaly(anchor, 'deny_cluster')
    },
    [handleExplainAnomaly],
  )

  /** Explain a single event from the EventDetailDrawer. */
  const handleExplainEvent = useCallback(
    (event: AuditLogEntry) => {
      const params: Record<string, unknown> = {
        event_ids: [event.id],
        max_events: 1,
        focus_hint: `Explain this single ${event.decision} request: the policy rationale (use deny_reason if present), what the actor attempted, and whether this looks routine or suspicious.`,
      }
      const scopeLabel = `Single event — #${event.entry_hash.slice(0, 8)}`
      return runSummary(params, scopeLabel)
    },
    [runSummary],
  )

  // ── AI Lenses (P3) ───────────────────────────────────────────

  /** Lens: focus on denied requests in the visible window. */
  const handleExplainDenials = useCallback(() => {
    const denials = entries.filter((e) => e.decision === 'deny' || e.decision === 'denied')
    const params = buildVisibleScopeParams()
    // Force-narrow to denials regardless of the user's Decision filter setting
    params.decision = 'denied'
    params.focus_hint =
      'Focus on denials only. Group by deny_reason, identify the top root causes, list affected agents/endpoints, and recommend operational fixes (policy, key rotation, capabilities). Skip allowed traffic.'
    const scopeLabel = `Denials lens — ${denials.length} denied event${denials.length === 1 ? '' : 's'} in view`
    return runSummary(params, scopeLabel)
  }, [entries, buildVisibleScopeParams, runSummary])

  /** Lens: focus on anomalies (deny clusters, latency spikes, cost outliers). */
  const handleSpotAnomalies = useCallback(() => {
    const anomalyMap = detectAnomalies(entries)
    const anomalousIds = Array.from(anomalyMap.keys())
    if (anomalousIds.length === 0) {
      // Defensive — the menu disables this when there are no anomalies, but if
      // the user invokes it via keyboard before state updates, fall back to
      // visible-scope explanation.
      return handleSummarize()
    }
    // Tally by category so the LLM has accurate counts up front.
    let denyClusters = 0
    let latencySpikes = 0
    let costOutliers = 0
    for (const flags of anomalyMap.values()) {
      for (const f of flags) {
        if (f.type === 'deny_cluster') denyClusters++
        else if (f.type === 'latency_spike') latencySpikes++
        else if (f.type === 'cost_outlier') costOutliers++
      }
    }
    const params: Record<string, unknown> = {
      event_ids: anomalousIds,
      max_events: Math.max(anomalousIds.length, 1),
      focus_hint: `${anomalousIds.length} flagged anomalies: ${denyClusters} deny clusters, ${latencySpikes} latency spikes, ${costOutliers} cost outliers. Explain each category, flag which warrant investigation vs operational noise, and recommend monitoring thresholds.`,
    }
    const scopeLabel = `Anomalies lens — ${anomalousIds.length} flagged event${anomalousIds.length === 1 ? '' : 's'}`
    return runSummary(params, scopeLabel)
  }, [entries, runSummary, handleSummarize])

  /** Lens: actor-ordered narrative — who did what, in what order. */
  const handleReconstructActors = useCallback(() => {
    const params = buildVisibleScopeParams()
    params.focus_hint =
      'Build an actor-ordered narrative. For each user_id/agent_id, list operations chronologically. Highlight privilege-sensitive actions (key rotation, revocation, policy changes) and unusual ordering.'
    const scopeLabel = `Actor timeline — ${entries.length} event${entries.length === 1 ? '' : 's'} in view`
    return runSummary(params, scopeLabel)
  }, [entries.length, buildVisibleScopeParams, runSummary])

  /** Dispatch a lens selection from the AILensMenu. */
  const handleLensSelect = useCallback(
    (lens: 'explain_visible' | 'explain_denials' | 'spot_anomalies' | 'reconstruct_actors') => {
      switch (lens) {
        case 'explain_visible':
          return handleSummarize()
        case 'explain_denials':
          return handleExplainDenials()
        case 'spot_anomalies':
          return handleSpotAnomalies()
        case 'reconstruct_actors':
          return handleReconstructActors()
      }
    },
    [handleSummarize, handleExplainDenials, handleSpotAnomalies, handleReconstructActors],
  )

  /** Memoize hasDenials/hasAnomalies for the lens menu so it can disable empty lenses. */
  const visibleHasDenials = useMemo(
    () => entries.some((e) => e.decision === 'deny' || e.decision === 'denied'),
    [entries],
  )
  const visibleHasAnomalies = useMemo(() => detectAnomalies(entries).size > 0, [entries])

  // ── Pagination ────────────────────────────────────────────────

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  // Anomaly detection for table view highlighting
  const anomalyMap = useMemo(() => detectAnomalies(entries), [entries])

  // ── Proactive alerts (P4) ─────────────────────────────────────

  /** Dismissed-alert fingerprints, persisted in sessionStorage so navigating
   *  away and back does not re-prompt. New fingerprints (different anomaly)
   *  re-trigger the banner. Cleared on tab close. */
  const SESSION_KEY = 'forensics-dismissed-alerts'
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(() => {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY)
      return raw ? new Set(JSON.parse(raw) as string[]) : new Set()
    } catch {
      return new Set()
    }
  })

  const handleDismissAlert = useCallback((fingerprint: string) => {
    setDismissedAlerts((prev) => {
      const next = new Set(prev)
      next.add(fingerprint)
      try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(Array.from(next)))
      } catch {
        // sessionStorage may be unavailable (private mode, quota) — fail silent
      }
      return next
    })
  }, [])

  /** Alerts derived from current anomalies + chain status. Filtered by
   *  dismissal fingerprints. */
  const alerts = useMemo<ForensicsAlert[]>(() => {
    const out: ForensicsAlert[] = []

    // 1. Largest deny cluster — pick the event whose detail reports the
    //    highest count, use it as the anchor for "Investigate cluster".
    let topCluster: { event: AuditLogEntry; count: number } | null = null
    for (const [eventId, flags] of anomalyMap) {
      const cluster = flags.find((f) => f.type === 'deny_cluster')
      if (!cluster) continue
      const match = cluster.detail.match(/^(\d+)/)
      const n = match ? parseInt(match[1], 10) : 0
      if (!topCluster || n > topCluster.count) {
        const event = entries.find((e) => e.id === eventId)
        if (event) topCluster = { event, count: n }
      }
    }
    if (topCluster) {
      const anchorIso = topCluster.event.created_at
      const fingerprint = `dc:${topCluster.count}:${anchorIso}`
      const anchor = topCluster.event
      const cnt = topCluster.count
      out.push({
        fingerprint,
        severity: 'high',
        icon: '🚨',
        title: `Deny cluster detected — ${cnt} denies within 60s`,
        description: `Anchor: ${new Date(anchorIso).toLocaleString()}. Narrows the table to this window and asks the AI for likely root cause + remediation.`,
        ctaLabel: 'Investigate cluster',
        onCTA: () => handleInvestigateCluster(anchor),
      })
    }

    // 2. Chain integrity break — only when the user has run Verify and it failed.
    if (chainValid === false) {
      const fingerprint = `cb:${chainMessage || 'broken'}`
      out.push({
        fingerprint,
        severity: 'high',
        icon: '⛓️',
        title: 'Audit chain integrity broken',
        description:
          chainMessage ||
          'HMAC verification failed. The audit trail may have been tampered with or has data corruption.',
        ctaLabel: 'See anomalies',
        onCTA: () => handleSpotAnomalies(),
      })
    }

    // 3. Aggregate latency / cost spikes — medium severity, only when meaningful.
    let latencySpikes = 0
    let costOutliers = 0
    for (const flags of anomalyMap.values()) {
      for (const f of flags) {
        if (f.type === 'latency_spike') latencySpikes++
        else if (f.type === 'cost_outlier') costOutliers++
      }
    }
    if (latencySpikes >= 3 || costOutliers >= 2) {
      const fingerprint = `agg:${latencySpikes}:${costOutliers}`
      const parts: string[] = []
      if (latencySpikes >= 3) parts.push(`${latencySpikes} latency spikes`)
      if (costOutliers >= 2) parts.push(`${costOutliers} cost outliers`)
      out.push({
        fingerprint,
        severity: 'medium',
        icon: '📊',
        title: `Performance anomalies detected`,
        description: `${parts.join(' and ')} above the agent's baseline. AI can flag which warrant investigation.`,
        ctaLabel: 'Spot anomalies',
        onCTA: () => handleSpotAnomalies(),
      })
    }

    return out.filter((a) => !dismissedAlerts.has(a.fingerprint))
  }, [
    anomalyMap,
    entries,
    chainValid,
    chainMessage,
    dismissedAlerts,
    handleInvestigateCluster,
    handleSpotAnomalies,
  ])

  /** When a HIGH-severity alert is showing (deny cluster, chain break), the
   *  banner already provides a focused CTA — surfacing the broad lens menu
   *  alongside it creates two competing buttons about the same data. We hide
   *  the lens menu in that case. Medium banners (perf anomalies) cover only
   *  one intent so the lens menu stays available. */
  const hasHighSeverityAlert = useMemo(() => alerts.some((a) => a.severity === 'high'), [alerts])

  // ── Filter summary bar ────────────────────────────────────────

  /** Window readout, always shown (e.g. "Apr 9, 2:39 AM → Jun 16, 2:39 AM"). */
  const windowLabel = `${shortDateLabel(startDate)} → ${shortDateLabel(endDate)}`

  /** Removable chips for every active (non-default) filter. The date window is
   *  a chip only when narrowed off the frozen default — clearing it restores
   *  the default 7-day view (so an alert drill-down is reversible). */
  const filterChips = useMemo<FilterChip[]>(() => {
    const out: FilterChip[] = []
    const windowIsCustom =
      startDate !== defaultWindow.current.start || endDate !== defaultWindow.current.end
    if (windowIsCustom) {
      out.push({ key: 'window', label: `Window: ${windowLabel}`, onClear: resetWindow })
    }
    if (selectedAgent) {
      const a = agents.find((x) => x.id === selectedAgent)
      out.push({
        key: 'agent',
        label: `Agent: ${a ? a.name : selectedAgent.slice(0, 8)}`,
        onClear: () => {
          setSelectedAgent('')
          setOffset(0)
        },
      })
    }
    if (filterDecision) {
      out.push({
        key: 'decision',
        label: `Decision: ${filterDecision}`,
        onClear: () => {
          setFilterDecision('')
          setOffset(0)
        },
      })
    }
    if (filterEndpoint) {
      out.push({
        key: 'endpoint',
        label: `Endpoint: ${filterEndpoint}`,
        onClear: () => {
          setFilterEndpoint('')
          setOffset(0)
        },
      })
    }
    if (filterActionType) {
      out.push({
        key: 'action type',
        label: `Action: ${filterActionType}`,
        onClear: () => {
          setFilterActionType('')
          setOffset(0)
        },
      })
    }
    if (filterModel) {
      out.push({
        key: 'model',
        label: `Model: ${filterModel}`,
        onClear: () => {
          setFilterModel('')
          setOffset(0)
        },
      })
    }
    if (filterCostMin || filterCostMax) {
      out.push({
        key: 'cost',
        label: `Cost: $${filterCostMin || '0'}–${filterCostMax ? `$${filterCostMax}` : '∞'}`,
        onClear: () => {
          setFilterCostMin('')
          setFilterCostMax('')
          setOffset(0)
        },
      })
    }
    return out
  }, [
    startDate,
    endDate,
    windowLabel,
    resetWindow,
    selectedAgent,
    agents,
    filterDecision,
    filterEndpoint,
    filterActionType,
    filterModel,
    filterCostMin,
    filterCostMax,
  ])

  /** Reset every filter and restore the default 7-day window — returns the page
   *  to its initial view in one click. */
  const handleClearAllFilters = useCallback(() => {
    setSelectedAgent('')
    setFilterDecision('')
    setFilterEndpoint('')
    setFilterActionType('')
    setFilterModel('')
    setFilterCostMin('')
    setFilterCostMax('')
    resetWindow()
  }, [resetWindow])

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Drag-and-drop verifier — drop a downloaded Case File, no CLI needed */}
      <CaseFileVerifyPanel />

      {/* Public-key-only inclusion verifier — proves a single event is committed
          to a signed checkpoint, entirely client-side (no shared secret) */}
      <InclusionProofPanel />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Case File</h1>
          <p className="text-sm text-muted mt-1">
            Court-ready evidence — HMAC-chained audit logs and DSSE-signed session attestations,
            verifiable offline
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {['FRE 702 / Daubert', 'ISO/IEC 27037', 'OCSF export', 'HMAC-SHA256 chain'].map((s) => (
              <span
                key={s}
                className="rounded-md border border-line bg-surface px-2.5 py-1 text-xs text-muted"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Tamper-evidence check — on-demand HMAC chain verification.
              Click runs cryptographic verification of every audit row; the
              result pill shows what was checked and is clickable to re-run. */}
          {chainValid !== null ? (
            <button
              onClick={handleVerifyChain}
              disabled={chainVerifying}
              title={
                chainValid
                  ? `${chainEntriesVerified.toLocaleString()} audit entries verified across the entire chain — independent of the date range and filters shown on the page (HMAC chain integrity is end-to-end by design). Each row's HMAC-SHA256 hash was recomputed and matched the stored value, and the prev_hash links were unbroken — proving no rows were modified, deleted, or reordered. Click to re-run.`
                  : `Tampering detected${chainFirstBrokenId !== null ? ` at entry #${chainFirstBrokenId}` : ''}. ${chainMessage} Click to re-run.`
              }
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                chainValid
                  ? 'bg-success-soft text-success border border-success hover:bg-success-soft'
                  : 'bg-danger-soft text-danger border border-danger hover:bg-danger-soft'
              }`}
            >
              {chainVerifying ? (
                <>
                  <svg
                    className="h-3 w-3 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Re-checking...
                </>
              ) : chainValid ? (
                <>
                  <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  Tamper-Evident · {chainEntriesVerified.toLocaleString()}{' '}
                  {chainEntriesVerified === 1 ? 'entry' : 'entries'} verified
                  <span className="text-success/60 ml-0.5">(full chain)</span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3 w-3 opacity-70"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                </>
              ) : (
                <>
                  <span className="h-1.5 w-1.5 rounded-full bg-danger" />
                  Tampering Detected
                  {chainFirstBrokenId !== null && ` · entry #${chainFirstBrokenId}`}
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3 w-3 opacity-70"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleVerifyChain}
              disabled={chainVerifying}
              title="Run cryptographic verification of the entire audit chain — independent of the date range and filters shown on the page (chain integrity is end-to-end by design). Recomputes each row's HMAC-SHA256 hash and checks the prev_hash links to prove no entries were modified, deleted, or reordered. Same algorithm runs in the offline CLI auditors can use."
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border border-line-strong text-muted hover:text-ink hover:border-line-strong transition-colors disabled:opacity-50"
            >
              {chainVerifying ? (
                <>
                  <svg
                    className="h-3 w-3 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Verifying...
                </>
              ) : (
                <>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3.5 w-3.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.403 12.652a3 3 0 000-5.304 3 3 0 00-3.75-3.751 3 3 0 00-5.305 0 3 3 0 00-3.751 3.75 3 3 0 000 5.305 3 3 0 003.75 3.751 3 3 0 005.305 0 3 3 0 003.751-3.75zm-2.546-4.46a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Tamper Evidence Check
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3 w-3 opacity-70"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                </>
              )}
            </button>
          )}

          {!hasHighSeverityAlert && (
            <AILensMenu
              visibleCount={entries.length}
              hasDenials={visibleHasDenials}
              hasAnomalies={visibleHasAnomalies}
              loading={summaryLoading}
              onSelect={handleLensSelect}
            />
          )}
          <ExportMenu
            items={[
              {
                label: 'JSON report',
                hint: 'Full report + reliability statement',
                onClick: exportJSON,
              },
              { label: 'CSV', hint: 'Flat event table', onClick: exportCSV },
              {
                label: 'OCSF',
                hint: 'API Activity (class_uid 6003) for SIEMs',
                onClick: exportOcsf,
              },
              {
                label: 'Verification bundle',
                hint: 'Signed .zip + offline verify CLI',
                onClick: exportBundle,
              },
            ]}
          />
        </div>
      </div>

      {/* Deep-linked shadow agent banner */}
      {deepLinkedAgentId && (
        <div className="flex items-center justify-between bg-ai-soft border border-ai rounded-xl px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-ai-soft border border-ai px-2.5 py-0.5 text-xs font-medium text-ai">
              Shadow Agent
            </span>
            <span className="text-sm font-mono text-muted">{deepLinkedAgentId}</span>
          </div>
          <button
            onClick={() => {
              setDeepLinkedAgentId(null)
              setOffset(0)
            }}
            className="text-xs text-muted hover:text-ink transition-colors"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Proactive anomaly alerts */}
      <ForensicsAlertBanner alerts={alerts} onDismiss={handleDismissAlert} />

      {/* Persistent filter-state summary — window is always visible */}
      <FilterSummaryBar
        total={total}
        windowLabel={windowLabel}
        chips={filterChips}
        onClearAll={handleClearAllFilters}
      />

      {/* Filters */}
      <div className="bg-surface border border-line rounded-xl p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Agent selector */}
          <div>
            <label className="block text-xs text-subtle mb-1">Agent</label>
            <select
              value={selectedAgent}
              onChange={(e) => {
                setSelectedAgent(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand"
            >
              <option value="">All Agents</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.id.slice(0, 8)})
                </option>
              ))}
            </select>
          </div>

          {/* Start date */}
          <div>
            <label className="block text-xs text-subtle mb-1">From</label>
            <input
              type="datetime-local"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>

          {/* End date */}
          <div>
            <label className="block text-xs text-subtle mb-1">To</label>
            <input
              type="datetime-local"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>

          {/* Decision filter */}
          <div>
            <label className="block text-xs text-subtle mb-1">Decision</label>
            <select
              value={filterDecision}
              onChange={(e) => {
                setFilterDecision(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand"
            >
              <option value="">All</option>
              <option value="allowed">Allowed</option>
              <option value="denied">Denied</option>
              <option value="error">Error</option>
            </select>
          </div>

          {/* Endpoint search */}
          <div>
            <label className="block text-xs text-subtle mb-1">Endpoint</label>
            <input
              type="text"
              value={filterEndpoint}
              onChange={(e) => {
                setFilterEndpoint(e.target.value)
                setOffset(0)
              }}
              placeholder="/v1/chat"
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 placeholder-faint focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>
        </div>

        {/* Metadata filters row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
          {/* Action type */}
          <div>
            <label className="block text-xs text-subtle mb-1">Action Type</label>
            <select
              value={filterActionType}
              onChange={(e) => {
                setFilterActionType(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand"
            >
              <option value="">All</option>
              <option value="agent_created">agent_created</option>
              <option value="key_rotated">key_rotated</option>
              <option value="policy_updated">policy_updated</option>
              <option value="credential_stored">credential_stored</option>
              <option value="agent_suspended">agent_suspended</option>
              <option value="agent_deleted">agent_deleted</option>
            </select>
          </div>

          {/* Model */}
          <div>
            <label className="block text-xs text-subtle mb-1">Model</label>
            <select
              value={filterModel}
              onChange={(e) => {
                setFilterModel(e.target.value)
                setOffset(0)
              }}
              className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand"
            >
              <option value="">All</option>
              <option value="gpt-4">gpt-4</option>
              <option value="gpt-4o">gpt-4o</option>
              <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
              <option value="claude-3-opus">claude-3-opus</option>
              <option value="claude-3-sonnet">claude-3-sonnet</option>
              <option value="claude-3-haiku">claude-3-haiku</option>
            </select>
          </div>

          {/* Cost range */}
          <div className="sm:col-span-2">
            <label className="block text-xs text-subtle mb-1">Cost Range (USD)</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={filterCostMin}
                onChange={(e) => {
                  setFilterCostMin(e.target.value)
                  setOffset(0)
                }}
                placeholder="Min"
                step="0.001"
                min="0"
                className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 placeholder-faint focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-subtle text-sm">–</span>
              <input
                type="number"
                value={filterCostMax}
                onChange={(e) => {
                  setFilterCostMax(e.target.value)
                  setOffset(0)
                }}
                placeholder="Max"
                step="0.001"
                min="0"
                className="w-full rounded-lg bg-surface border border-line text-ink text-sm px-3 py-2 placeholder-faint focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </div>
          </div>
        </div>

        {/* Investigate button */}
        {effectiveAgentId && (
          <div className="mt-3 pt-3 border-t border-line">
            <button
              onClick={handleReconstruct}
              disabled={reconstructing}
              className="px-4 py-2 text-sm font-medium text-brand-ink bg-brand hover:bg-brand-hover disabled:opacity-50 rounded-lg transition-colors inline-flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" />
              </svg>
              {reconstructing ? 'Reconstructing...' : 'Investigate Incident'}
            </button>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-surface border border-line rounded-xl p-4">
            <div className="text-xs text-subtle uppercase tracking-wider">Total Events</div>
            <div className="text-2xl font-bold text-brand mt-1">
              {stats.total_events.toLocaleString()}
            </div>
          </div>
          <div className="bg-surface border border-line rounded-xl p-4">
            <div className="text-xs text-success uppercase tracking-wider">Allowed</div>
            <div className="text-2xl font-bold text-success mt-1">
              {stats.allowed_count.toLocaleString()}
            </div>
          </div>
          <div className="bg-surface border border-line rounded-xl p-4">
            <div className="text-xs text-danger uppercase tracking-wider">Denied</div>
            <div className="text-2xl font-bold text-danger mt-1">
              {stats.denied_count.toLocaleString()}
            </div>
          </div>
          <div className="bg-surface border border-line rounded-xl p-4">
            <div className="text-xs text-warning uppercase tracking-wider">Errors</div>
            <div className="text-2xl font-bold text-warning mt-1">
              {stats.error_count.toLocaleString()}
            </div>
          </div>
          <div className="bg-surface border border-line rounded-xl p-4">
            <div className="text-xs text-subtle uppercase tracking-wider">Total Cost</div>
            <div className="text-2xl font-bold text-ink mt-1">
              ${stats.total_cost_usd.toFixed(2)}
            </div>
          </div>
          <div className="bg-surface border border-line rounded-xl p-4">
            <div className="text-xs text-subtle uppercase tracking-wider">Avg Latency</div>
            <div className="text-2xl font-bold text-ink mt-1">
              {stats.avg_latency_ms != null ? `${stats.avg_latency_ms}ms` : '--'}
            </div>
          </div>
        </div>
      )}

      {/* View Toggle (results count now lives in the filter summary bar) */}
      <div className="flex items-center justify-end">
        <div className="flex items-center gap-1 bg-elevated rounded-lg p-0.5 border border-line">
          <button
            onClick={() => setViewMode('timeline')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'timeline' ? 'bg-brand text-brand-ink' : 'text-muted hover:text-ink'
            }`}
          >
            Timeline
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'table' ? 'bg-brand text-brand-ink' : 'text-muted hover:text-ink'
            }`}
          >
            Table
          </button>
        </div>
      </div>

      {/* Hash Chain Visualization */}
      {entries.length > 1 && <HashChainView events={entries} />}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-subtle">
          Loading audit events...
        </div>
      ) : viewMode === 'timeline' ? (
        <div className="bg-surface border border-line rounded-xl p-6">
          <ForensicsTimeline
            events={entries}
            onEventClick={setSelectedEvent}
            onExplainAnomaly={handleExplainAnomaly}
          />
        </div>
      ) : (
        /* Table View */
        <div className="bg-surface border border-line rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-subtle uppercase tracking-wider">
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Decision</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3">Endpoint</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {entries.map((e) => {
                  const rowAnomalies = anomalyMap.get(e.id)
                  const hasDenyCluster = rowAnomalies?.some((a) => a.type === 'deny_cluster')
                  const hasLatencyOrCost = rowAnomalies?.some(
                    (a) => a.type === 'latency_spike' || a.type === 'cost_outlier',
                  )
                  const rowBg = hasDenyCluster
                    ? 'bg-danger-soft'
                    : hasLatencyOrCost
                      ? 'bg-anomaly-soft'
                      : ''
                  return (
                    <tr
                      key={e.id}
                      className={`hover:bg-elevated transition-colors cursor-pointer ${rowBg}`}
                      onClick={() => setSelectedEvent(e)}
                    >
                      <td className="px-4 py-3 text-muted whitespace-nowrap">
                        {formatDate(e.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${decisionBadge(e.decision)}`}
                        >
                          {e.decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted font-mono text-xs">{e.method}</td>
                      <td className="px-4 py-3 text-muted font-mono text-xs max-w-xs truncate">
                        {e.endpoint}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {e.cost_estimate_usd != null ? `$${e.cost_estimate_usd.toFixed(4)}` : '--'}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {e.latency_ms != null ? `${e.latency_ms}ms` : '--'}
                      </td>
                      <td className="px-4 py-3 text-faint font-mono text-xs">
                        {e.entry_hash.slice(0, 12)}...
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-sm text-subtle">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="px-3 py-1.5 text-sm font-medium text-muted bg-elevated hover:bg-elevated disabled:opacity-40 rounded-lg transition-colors border border-line-strong"
            >
              Previous
            </button>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={offset + limit >= total}
              className="px-3 py-1.5 text-sm font-medium text-muted bg-elevated hover:bg-elevated disabled:opacity-40 rounded-lg transition-colors border border-line-strong"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Top Endpoints */}
      {stats && stats.top_endpoints.length > 0 && (
        <div className="bg-surface border border-line rounded-xl p-6">
          <h3 className="text-sm font-medium text-muted mb-3">Top Endpoints</h3>
          <div className="space-y-2">
            {stats.top_endpoints.map((ep) => {
              const pct = stats.total_events > 0 ? (ep.count / stats.total_events) * 100 : 0
              return (
                <div key={ep.endpoint} className="flex items-center gap-3">
                  <span className="text-xs font-mono text-muted w-48 truncate">{ep.endpoint}</span>
                  <div className="flex-1 bg-elevated rounded-full h-2">
                    <div
                      className="bg-brand h-2 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-subtle w-16 text-right">
                    {ep.count} ({pct.toFixed(0)}%)
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Incident Reconstruction Modal */}
      {reconstructData && (
        <IncidentReconstructModal
          data={reconstructData}
          onClose={() => setReconstructData(null)}
          onExportJSON={exportJSON}
          onExportCSV={exportCSV}
        />
      )}

      {/* Event Detail Drawer */}
      {selectedEvent && (
        <EventDetailDrawer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          events={entries}
          onNavigate={setSelectedEvent}
          onExplain={handleExplainEvent}
        />
      )}

      {/* AI Summary Panel */}
      {showSummaryPanel && (
        <AISummaryPanel
          data={summaryData}
          loading={summaryLoading}
          error={summaryError}
          scopeLabel={summaryScope}
          onClose={() => setShowSummaryPanel(false)}
          onRegenerate={handleRegenerate}
        />
      )}
    </div>
  )
}
