/**
 * Billing & usage API client functions.
 */

import { apiFetch } from './client'

// ── Types ────────────────────────────────────────────────────────

export interface QuotaUsage {
  current: number
  limit: number | null
  unlimited: boolean
  percentage: number
}

export interface UsageSummary {
  tier: string
  agents: QuotaUsage
  active_keys: QuotaUsage
  credentials: QuotaUsage
  requests_this_month: QuotaUsage
  audit_retention_days: number
}

export interface TierInfo {
  name: string
  max_agents: number
  max_keys_per_agent: number
  max_requests_per_month: number
  max_credentials: number
  audit_retention_days: number
}

export interface TierList {
  tiers: TierInfo[]
  current_tier: string
}

export interface DailyUsagePoint {
  date: string
  total_requests: number
  allowed: number
  denied: number
  errors: number
}

export interface AgentUsageBreakdown {
  agent_id: string
  agent_name: string
  agent_status: string
  total_requests: number
  allowed: number
  denied: number
  last_active: string | null
}

export interface BillingPeriodSummary {
  period_start: string
  period_end: string
  total_requests: number
  allowed: number
  denied: number
  errors: number
  agents_seen: number
  peak_daily_requests: number
  avg_daily_requests: number
}

export interface UsageAggregation {
  tier: string
  billing_period: BillingPeriodSummary
  previous_period: BillingPeriodSummary | null
  daily: DailyUsagePoint[]
  by_agent: AgentUsageBreakdown[]
}

export interface BillingStatus {
  tier: string
  has_billing_account: boolean
  has_subscription: boolean
  stripe_customer_id: string | null
  subscription?: {
    id: string
    status: string
    current_period_start: number
    current_period_end: number
    cancel_at_period_end: boolean
  } | null
}

export interface CheckoutResponse {
  checkout_url: string
  session_id: string
}

export interface PortalResponse {
  portal_url: string
}

// ── API functions ────────────────────────────────────────────────

export function getUsageSummary(): Promise<UsageSummary> {
  return apiFetch<UsageSummary>('/api/v1/usage')
}

export function getUsageAggregation(): Promise<UsageAggregation> {
  return apiFetch<UsageAggregation>('/api/v1/usage/aggregation')
}

export function getTiers(): Promise<TierList> {
  return apiFetch<TierList>('/api/v1/usage/tiers')
}

export function getBillingStatus(): Promise<BillingStatus> {
  return apiFetch<BillingStatus>('/api/v1/billing/status')
}

export function createCheckoutSession(plan: string = 'pro'): Promise<CheckoutResponse> {
  return apiFetch<CheckoutResponse>(`/api/v1/billing/checkout?plan=${plan}`, {
    method: 'POST',
  })
}

export function createPortalSession(): Promise<PortalResponse> {
  return apiFetch<PortalResponse>('/api/v1/billing/portal', {
    method: 'POST',
  })
}
