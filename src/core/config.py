"""Core configuration module for the barbershop booking agent.

This module provides centralized configuration management using Pydantic settings.
It loads configuration from environment variables and provides typed access to
all application settings.

Example:
    >>> from src.core.config import get_settings
    >>> settings = get_settings()
    >>> print(settings.app_name)
    "Tony's Barbershop Booking Agent"
"""

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden by environment variables. The .env file
    is automatically loaded if present.

    Attributes:
        app_name: Name of the application.
        app_version: Current version of the application.
        environment: Deployment environment (development, staging, production).
        debug: Enable debug mode with additional logging.
        openai_api_key: OpenAI API key for LLM access.
        openai_model: Model name to use (e.g., gpt-4, gpt-3.5-turbo).
        openai_temperature: Temperature for LLM responses (0.0-1.0).
        openai_max_tokens: Maximum tokens per LLM response.
        langchain_tracing_v2: Enable LangSmith tracing.
        langchain_api_key: LangSmith API key for observability.
        langchain_project: Project name in LangSmith.
        langchain_endpoint: LangSmith API endpoint.
        api_host: Host address for FastAPI server.
        api_port: Port for FastAPI server.
        api_reload: Enable auto-reload for development.
        api_workers: Number of worker processes.
        chainlit_host: Host address for Chainlit UI.
        chainlit_port: Port for Chainlit UI.
        chainlit_auth_secret: Secret key for Chainlit authentication.
        database_url: Database connection URL.
        db_pool_size: Database connection pool size.
        db_max_overflow: Maximum overflow connections.
        db_pool_timeout: Connection timeout in seconds.
        db_pool_recycle: Connection recycle time in seconds.
        cors_origins: Allowed CORS origins.
        cors_credentials: Allow credentials in CORS requests.
        cors_methods: Allowed HTTP methods.
        cors_headers: Allowed HTTP headers.
        agent_max_iterations: Maximum agent loop iterations.
        agent_timeout_seconds: Agent execution timeout.
        conversation_memory_window: Number of messages to keep in memory.
        business_name: Name of the barbershop.
        business_phone: Business phone number.
        business_email: Business email address.
        business_address: Physical business address.
        business_timezone: Timezone for business operations.
        business_hours: Operating hours by day of week.
        booking_slot_duration_minutes: Duration of each booking slot.
        booking_advance_days: Maximum days to book in advance.
        cancellation_notice_hours: Required cancellation notice.
        same_day_booking_cutoff_hour: Latest hour for same-day bookings.
        log_level: Logging level.
        log_format: Log format (json or text).
        log_file: Path to log file.
        secret_key: Secret key for JWT and encryption.
        algorithm: Algorithm for JWT encoding.
        access_token_expire_minutes: Token expiration time.
        rate_limit_enabled: Enable rate limiting.
        rate_limit_per_minute: Maximum requests per minute.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Tony's Barbershop Booking Agent")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # LLM Configuration
    llm_provider: str = Field(default="azure_openai")  # "openai" or "azure_openai"
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4")
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    openai_max_tokens: int = Field(default=1000, gt=0)

    # Azure OpenAI Configuration
    azure_openai_api_key: SecretStr = Field(default=SecretStr(""))
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_version: str = Field(default="2025-03-01-preview")
    azure_openai_deployment_name: str = Field(default="")

    # LangSmith
    langchain_tracing_v2: bool = Field(default=False)
    langchain_api_key: str = Field(default="")
    langchain_project: str = Field(default="barbershop-booking-agent")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com")

    # FastAPI
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8005)
    api_reload: bool = Field(default=True)
    api_workers: int = Field(default=1)

    # Chainlit
    chainlit_host: str = Field(default="0.0.0.0")
    chainlit_port: int = Field(default=8001)
    chainlit_auth_secret: str = Field(default="change-me-in-production")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./barbershop.db")
    db_pool_size: int = Field(default=5)
    db_max_overflow: int = Field(default=10)
    db_pool_timeout: int = Field(default=30)
    db_pool_recycle: int = Field(default=3600)

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:8005", "http://localhost:3000"])
    cors_credentials: bool = Field(default=True)
    cors_methods: list[str] = Field(default=["*"])
    cors_headers: list[str] = Field(default=["*"])

    # Agent Configuration
    agent_max_iterations: int = Field(default=10, gt=0)
    agent_timeout_seconds: int = Field(default=60, gt=0)
    conversation_memory_window: int = Field(default=10, gt=0)

    # Business Configuration (loaded from database/YAML, not hardcoded)
    business_name: str = Field(default="")
    business_phone: str = Field(default="")
    business_email: str = Field(default="")
    business_address: str = Field(default="")
    business_timezone: str = Field(default="America/New_York")
    business_hours: dict[str, dict[str, str]] = Field(default_factory=dict)

    # Booking Configuration (loaded from database/YAML)
    booking_slot_duration_minutes: int = Field(default=30, gt=0)
    booking_advance_days: int = Field(default=14, gt=0)
    cancellation_notice_hours: int = Field(default=24, gt=0)
    same_day_booking_cutoff_hour: int = Field(default=14, ge=0, le=23)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: str = Field(default="logs/barbershop.log")

    # Security
    secret_key: str = Field(default="change-me-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=False)
    rate_limit_per_minute: int = Field(default=60)

    @field_validator("business_hours", mode="before")
    @classmethod
    def parse_business_hours(cls, v: Any) -> dict[str, dict[str, str]]:
        """Parse business hours from JSON string or dict.

        Args:
            v: Business hours as JSON string or dict.

        Returns:
            Parsed business hours dictionary.

        Raises:
            ValueError: If the format is invalid.
        """
        if isinstance(v, str):
            try:
                parsed: dict[str, dict[str, str]] = json.loads(v)
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for business_hours: {e}") from e
        # Assume v is already the correct dict type from pydantic
        return v  # type: ignore[no-any-return]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if environment is production, False otherwise.
        """
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if environment is development, False otherwise.
        """
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function uses lru_cache to ensure only one Settings instance
    is created and reused throughout the application lifecycle.

    Returns:
        Singleton Settings instance.

    Example:
        >>> settings = get_settings()
        >>> print(settings.app_name)
    """
    return Settings()
