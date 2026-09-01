/**
 * Edge deployments API — registered off-platform enforcement points and
 * the continuity of their ingested evidence streams.
 */

import { apiFetch } from './client'

export interface EdgeSummary {
  id: string
  name: string
  chain_uid: string
  authority_uid: string | null
  key_id: string | null
  ingest_key_prefix: string
  status: string
  created_at: string
  last_ingest_at: string | null
}

/**
 * One (epoch, stream_id) run of verified records — the unit density is
 * defined over. A NEW epoch on the same stream is a producer restart:
 * a boundary, not a loss. Two dense segments with a seq reset between
 * them is the healthy shape of a stream that survived a crash.
 */
export interface EdgeStreamSegment {
  stream_id: string
  epoch: number | null
  first_seq: number
  last_seq: number
  records: number
  dense: boolean
  anomaly_records: number
  last_received_at: string
}

export interface EdgeStreamsResponse {
  edge_id: string
  name: string
  chain_uid: string
  status: string
  last_ingest_at: string | null
  verified: number
  quarantined: number
  segments: EdgeStreamSegment[]
}

/** List the org's registered edge deployments. */
export async function listEdges(): Promise<{ edges: EdgeSummary[] }> {
  return apiFetch<{ edges: EdgeSummary[] }>('/api/v1/edges')
}

/** Continuity view of one edge's ingested stream, grouped by (epoch, stream). */
export async function fetchEdgeStreams(edgeId: string): Promise<EdgeStreamsResponse> {
  return apiFetch<EdgeStreamsResponse>(`/api/v1/edges/${edgeId}/streams`)
}
