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

    # Services
    api_port: int = 8001
    gateway_port: int = 8002

    # Environment
    environment: str = "development"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
