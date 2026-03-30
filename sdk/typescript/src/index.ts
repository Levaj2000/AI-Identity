export { AIIdentityClient } from "./client.js";
export type { AIIdentityClientOptions } from "./client.js";

// Errors
export {
  AIIdentityError,
  AuthenticationError,
  ForbiddenError,
  NotFoundError,
  RateLimitError,
  ValidationError,
} from "./errors.js";

// Types
export type {
  Agent,
  AgentCreate,
  AgentCreateResponse,
  AgentKey,
  AgentKeyCreateResponse,
  AgentKeyList,
  AgentKeyRotateResponse,
  AgentList,
  AgentListParams,
  AgentUpdate,
  AuditChainVerification,
  AuditEntry,
  AuditList,
  AuditListParams,
  AuditStats,
  Credential,
  CredentialCreate,
  CredentialCreateResponse,
  CredentialList,
  CredentialRotate,
  ListParams,
  Policy,
  PolicyCreate,
  TopEndpoint,
} from "./types.js";
