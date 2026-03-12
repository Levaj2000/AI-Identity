"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


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

    # Environment
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # App metadata
    app_version: str = "0.1.0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
