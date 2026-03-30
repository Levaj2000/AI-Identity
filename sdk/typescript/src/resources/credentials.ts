import { HttpClient } from "../http.js";
import type {
  Credential,
  CredentialCreate,
  CredentialCreateResponse,
  CredentialList,
  CredentialRotate,
} from "../types.js";

function base(agentId: string): string {
  return `/api/v1/agents/${agentId}/credentials`;
}

export class CredentialsResource {
  constructor(private readonly http: HttpClient) {}

  /** Store an upstream API key. It is encrypted at rest. */
  async create(agentId: string, data: CredentialCreate): Promise<CredentialCreateResponse> {
    return this.http.post<CredentialCreateResponse>(base(agentId), data);
  }

  /** List all credentials for an agent (metadata only). */
  async list(agentId: string): Promise<CredentialList> {
    return this.http.get<CredentialList>(base(agentId));
  }

  /** Rotate a credential's upstream API key. */
  async rotate(agentId: string, credentialId: number, data: CredentialRotate): Promise<Credential> {
    return this.http.put<Credential>(`${base(agentId)}/${credentialId}/rotate`, data);
  }

  /** Revoke an upstream credential. */
  async revoke(agentId: string, credentialId: number): Promise<Credential> {
    return this.http.delete<Credential>(`${base(agentId)}/${credentialId}`);
  }
}
