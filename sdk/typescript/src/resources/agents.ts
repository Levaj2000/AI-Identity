import { HttpClient } from "../http.js";
import type {
  Agent,
  AgentCreate,
  AgentCreateResponse,
  AgentList,
  AgentListParams,
  AgentUpdate,
} from "../types.js";

const BASE = "/api/v1/agents";

export class AgentsResource {
  constructor(private readonly http: HttpClient) {}

  /** Create a new agent and receive a show-once API key. */
  async create(data: AgentCreate): Promise<AgentCreateResponse> {
    return this.http.post<AgentCreateResponse>(BASE, data);
  }

  /** List agents with optional filters and pagination. */
  async list(params?: AgentListParams): Promise<AgentList> {
    return this.http.get<AgentList>(BASE, params as Record<string, unknown>);
  }

  /** Get a single agent by ID. */
  async get(agentId: string): Promise<Agent> {
    return this.http.get<Agent>(`${BASE}/${agentId}`);
  }

  /** Update an agent. Only include fields you want to change. */
  async update(agentId: string, data: AgentUpdate): Promise<Agent> {
    return this.http.put<Agent>(`${BASE}/${agentId}`, data);
  }

  /** Revoke (soft-delete) an agent. This is irreversible. */
  async delete(agentId: string): Promise<Agent> {
    return this.http.delete<Agent>(`${BASE}/${agentId}`);
  }
}
