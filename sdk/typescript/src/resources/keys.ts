import { HttpClient } from "../http.js";
import type {
  AgentKey,
  AgentKeyCreateResponse,
  AgentKeyList,
  AgentKeyRotateResponse,
} from "../types.js";

function base(agentId: string): string {
  return `/api/v1/agents/${agentId}/keys`;
}

export class KeysResource {
  constructor(private readonly http: HttpClient) {}

  /** Issue a new API key for an agent. Store the returned key securely. */
  async create(agentId: string): Promise<AgentKeyCreateResponse> {
    return this.http.post<AgentKeyCreateResponse>(base(agentId));
  }

  /** List all keys for an agent (prefixes and status only). */
  async list(agentId: string): Promise<AgentKeyList> {
    return this.http.get<AgentKeyList>(base(agentId));
  }

  /** Rotate a key. The old key enters a 24-hour grace period. */
  async rotate(agentId: string, keyId: number): Promise<AgentKeyRotateResponse> {
    return this.http.post<AgentKeyRotateResponse>(`${base(agentId)}/${keyId}/rotate`);
  }

  /** Revoke a key immediately. */
  async revoke(agentId: string, keyId: number): Promise<AgentKey> {
    return this.http.delete<AgentKey>(`${base(agentId)}/${keyId}`);
  }
}
