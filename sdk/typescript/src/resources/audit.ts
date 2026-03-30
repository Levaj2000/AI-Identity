import { HttpClient } from "../http.js";
import type {
  AuditChainVerification,
  AuditList,
  AuditListParams,
  AuditStats,
} from "../types.js";

const BASE = "/api/v1/audit";

export class AuditResource {
  constructor(private readonly http: HttpClient) {}

  /** List audit log entries with optional agent filter. */
  async list(params?: AuditListParams): Promise<AuditList> {
    return this.http.get<AuditList>(BASE, params as Record<string, unknown>);
  }

  /** Get aggregated audit statistics. */
  async stats(agentId?: string): Promise<AuditStats> {
    return this.http.get<AuditStats>(`${BASE}/stats`, { agent_id: agentId });
  }

  /** Verify the HMAC chain integrity for an agent's audit log. */
  async verifyChain(agentId: string): Promise<AuditChainVerification> {
    return this.http.get<AuditChainVerification>(`${BASE}/verify/${agentId}`);
  }
}
