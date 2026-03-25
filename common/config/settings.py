"""Application settings loaded from environment variables."""

import logging

from pydantic_settings import BaseSettings

_logger = logging.getLogger("ai_identity.config")


class Settings(BaseSettings):
    """Shared settings for API and Gateway services."""

    # Database
    database_url: str = "postgresql://localhost:5432/ai_identity"

    # Security
    api_key_prefix: str = "aid_sk_"
    admin_key_prefix: str = "aid_admin_"
    key_rotation_grace_hours: int = 24
    audit_hmac_key: str = "CHANGE-ME-IN-PRODUCTION"

    # Upstream credential encryption (Fernet)
    credential_encryption_key: str = ""

    # Internal service-to-service authentication (HMAC-SHA256)
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    internal_service_key: str = ""

    # Services
    api_port: int = 8001
    gateway_port: int = 8002

    # Gateway — fail-closed enforcement
    policy_eval_timeout_ms: int = 500
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_window_seconds: int = 60
    circuit_breaker_recovery_seconds: int = 30

    # Gateway — pre-policy rate limiting (in-memory sliding window)
    rate_limit_per_ip: int = 100
    rate_limit_per_key: int = 60
    rate_limit_window_seconds: int = 1
    rate_limit_enabled: bool = True

    # Audit debug logging — opt-in, PII-redacted, auto-expiring
    audit_debug_logging: bool = False
    audit_debug_ttl_hours: int = 24
    audit_debug_log_dir: str = "/tmp/ai-identity/audit-debug"

    # Stripe billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Stripe Price IDs — monthly
    stripe_price_id_pro: str = ""  # Pro monthly ($79/mo)
    stripe_price_id_business: str = ""  # Business monthly ($299/mo)
    stripe_price_id_enterprise: str = ""  # Enterprise (custom)
    # Stripe Price IDs — annual (15% discount)
    stripe_price_id_pro_annual: str = ""  # Pro annual ($67/mo → $804/yr)
    stripe_price_id_business_annual: str = ""  # Business annual ($254/mo → $3,048/yr)
    stripe_success_url: str = (
        "https://dashboard.ai-identity.co/settings?session_id={CHECKOUT_SESSION_ID}"
    )
    stripe_cancel_url: str = "https://dashboard.ai-identity.co/settings"

    # Clerk authentication
    # CLERK_ISSUER is the Clerk instance URL (e.g. https://your-app.clerk.accounts.dev)
    # Used to fetch JWKS for JWT verification. If empty, Clerk auth is disabled
    # and legacy X-API-Key auth is used.
    clerk_issuer: str = ""

    # Gateway URL (for QA runner — API needs to reach gateway)
    gateway_url: str = "http://localhost:8002"

    # Sentry error monitoring (leave empty to disable)
    sentry_dsn: str = ""

    # Environment
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # CORS
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,https://dashboard.ai-identity.co"
    )
    # Regex pattern for dynamic CORS origins (e.g. Vercel preview deploys)
    # Set to empty string to disable. Example:
    #   CORS_ORIGIN_REGEX=https://dashboard-.*-jeff-levas-projects\.vercel\.app
    cors_origin_regex: str = ""

    # App metadata
    app_version: str = "0.1.0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# Fail-closed: refuse to start with insecure defaults in production
if settings.environment != "development":
    if settings.audit_hmac_key == "CHANGE-ME-IN-PRODUCTION":
        raise SystemExit(
            "FATAL: AUDIT_HMAC_KEY is using the default value. "
            "Set a strong random key via environment variable before starting in production. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )
    if not settings.credential_encryption_key:
        _logger.warning(
            "CREDENTIAL_ENCRYPTION_KEY is empty — credential storage will fail until configured."
        )
