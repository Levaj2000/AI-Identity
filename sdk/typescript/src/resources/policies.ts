import { HttpClient } from "../http.js";
import type { Policy, PolicyCreate } from "../types.js";

function base(agentId: string): string {
  return `/api/v1/agents/${agentId}/policies`;
}

export class PoliciesResource {
  constructor(private readonly http: HttpClient) {}

  /** Create a new policy for an agent. */
  async create(agentId: string, data: PolicyCreate): Promise<Policy> {
    return this.http.post<Policy>(base(agentId), data);
  }

  /** List all policies for an agent. */
  async list(agentId: string): Promise<Policy[]> {
    return this.http.get<Policy[]>(base(agentId));
  }
}
