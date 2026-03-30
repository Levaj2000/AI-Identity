import { HttpClient } from "./http.js";
import { AgentsResource } from "./resources/agents.js";
import { AuditResource } from "./resources/audit.js";
import { CredentialsResource } from "./resources/credentials.js";
import { KeysResource } from "./resources/keys.js";
import { PoliciesResource } from "./resources/policies.js";

const DEFAULT_BASE_URL = "https://api.ai-identity.co";

export interface AIIdentityClientOptions {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

/**
 * AI Identity SDK client.
 *
 * @example
 * ```ts
 * const client = new AIIdentityClient({ apiKey: "aid_sk_..." });
 * const result = await client.agents.create({ name: "my-agent" });
 * console.log(result.api_key); // Store securely!
 * ```
 */
export class AIIdentityClient {
  readonly agents: AgentsResource;
  readonly keys: KeysResource;
  readonly policies: PoliciesResource;
  readonly credentials: CredentialsResource;
  readonly audit: AuditResource;

  constructor(options: AIIdentityClientOptions) {
    const http = new HttpClient(
      options.apiKey,
      options.baseUrl ?? DEFAULT_BASE_URL,
      { timeout: options.timeout },
    );
    this.agents = new AgentsResource(http);
    this.keys = new KeysResource(http);
    this.policies = new PoliciesResource(http);
    this.credentials = new CredentialsResource(http);
    this.audit = new AuditResource(http);
  }
}
