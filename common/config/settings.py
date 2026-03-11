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

    # Services
    api_port: int = 8001
    gateway_port: int = 8002

    # Gateway — fail-closed enforcement
    policy_eval_timeout_ms: int = 500
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_window_seconds: int = 60
    circuit_breaker_recovery_seconds: int = 30

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
