/** Base error for all AI Identity API errors. */
export class AIIdentityError extends Error {
  readonly statusCode: number;
  readonly errorCode: string;

  constructor(message: string, statusCode: number, errorCode: string) {
    super(message);
    this.name = "AIIdentityError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

/** Raised when the API key is missing or invalid (HTTP 401). */
export class AuthenticationError extends AIIdentityError {
  constructor(message: string, errorCode = "authentication_error") {
    super(message, 401, errorCode);
    this.name = "AuthenticationError";
  }
}

/** Raised when the API key lacks permission (HTTP 403). */
export class ForbiddenError extends AIIdentityError {
  constructor(message: string, errorCode = "forbidden") {
    super(message, 403, errorCode);
    this.name = "ForbiddenError";
  }
}

/** Raised when the resource does not exist (HTTP 404). */
export class NotFoundError extends AIIdentityError {
  constructor(message: string, errorCode = "not_found") {
    super(message, 404, errorCode);
    this.name = "NotFoundError";
  }
}

/** Raised when request data fails validation (HTTP 422). */
export class ValidationError extends AIIdentityError {
  constructor(message: string, errorCode = "validation_error") {
    super(message, 422, errorCode);
    this.name = "ValidationError";
  }
}

/** Raised when the rate limit is exceeded (HTTP 429). */
export class RateLimitError extends AIIdentityError {
  constructor(message: string, errorCode = "rate_limit_exceeded") {
    super(message, 429, errorCode);
    this.name = "RateLimitError";
  }
}
