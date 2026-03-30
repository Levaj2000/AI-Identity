import {
  AIIdentityError,
  AuthenticationError,
  ForbiddenError,
  NotFoundError,
  RateLimitError,
  ValidationError,
} from "./errors.js";

const ERROR_MAP: Record<number, new (msg: string, code: string) => AIIdentityError> = {
  401: AuthenticationError,
  403: ForbiddenError,
  404: NotFoundError,
  422: ValidationError,
  429: RateLimitError,
};

/** Build a query string from params, stripping undefined values. */
function toQueryString(params: Record<string, unknown>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null,
  );
  if (entries.length === 0) return "";
  const qs = entries
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return `?${qs}`;
}

export class HttpClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly timeout: number;

  constructor(apiKey: string, baseUrl: string, options?: { timeout?: number }) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.timeout = options?.timeout ?? 30_000;
    this.headers = {
      "X-API-Key": apiKey,
      "Content-Type": "application/json",
      "User-Agent": "ai-identity-typescript/0.1.0",
    };
  }

  private async request<T>(
    method: string,
    path: string,
    options?: { json?: unknown; params?: Record<string, unknown> },
  ): Promise<T> {
    const qs = options?.params ? toQueryString(options.params) : "";
    const url = `${this.baseUrl}${path}${qs}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: this.headers,
        body: options?.json ? JSON.stringify(options.json) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        await this.handleError(response);
      }

      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  private async handleError(response: Response): Promise<never> {
    const status = response.status;
    let errorCode = "unknown_error";
    let message = `HTTP ${status}`;

    try {
      const body = await response.json();
      if (body?.error) {
        errorCode = body.error.code ?? errorCode;
        message = body.error.message ?? message;
      } else if (body?.detail) {
        message = String(body.detail);
      }
    } catch {
      message = (await response.text().catch(() => "")) || message;
    }

    const ErrorClass = ERROR_MAP[status] ?? AIIdentityError;
    throw new ErrorClass(message, errorCode);
  }

  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    return this.request<T>("GET", path, { params });
  }

  async post<T>(path: string, json?: unknown): Promise<T> {
    return this.request<T>("POST", path, { json });
  }

  async put<T>(path: string, json?: unknown): Promise<T> {
    return this.request<T>("PUT", path, { json });
  }

  async patch<T>(path: string, json?: unknown): Promise<T> {
    return this.request<T>("PATCH", path, { json });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }
}
