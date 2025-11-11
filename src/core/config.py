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
        environment: Deployment environment (development, staging, production).
        debug: Enable debug mode with additional logging.
        llm_provider: LLM provider to use (openai or azure_openai).
        openai_api_key: OpenAI API key for LLM access.
        openai_model: Model name to use (e.g., gpt-4, gpt-3.5-turbo).
        openai_temperature: Temperature for LLM responses (0.0-1.0).
        azure_openai_api_key: Azure OpenAI API key.
        azure_openai_endpoint: Azure OpenAI endpoint URL.
        azure_openai_api_version: Azure OpenAI API version.
        azure_openai_deployment_name: Azure OpenAI deployment name.
        api_host: Host address for FastAPI server.
        api_port: Port for FastAPI server.
        api_reload: Enable auto-reload for development.
        database_url: Database connection URL.
        db_pool_size: Database connection pool size.
        db_max_overflow: Maximum overflow connections.
        db_pool_timeout: Connection timeout in seconds.
        db_pool_recycle: Connection recycle time in seconds.
        cors_origins: Allowed CORS origins.
        cors_credentials: Allow credentials in CORS requests.
        cors_methods: Allowed HTTP methods.
        cors_headers: Allowed HTTP headers.
        business_hours: Operating hours by day of week.
        booking_advance_days: Maximum days to book in advance.
        cancellation_notice_hours: Required cancellation notice.
        same_day_booking_cutoff_hour: Latest hour for same-day bookings.
        log_level: Logging level.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Tony's Barbershop Booking Agent")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # LLM Configuration
    llm_provider: str = Field(default="azure_openai")  # "openai" or "azure_openai"
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4")
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Azure OpenAI Configuration
    azure_openai_api_key: SecretStr = Field(default=SecretStr(""))
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_version: str = Field(default="2025-03-01-preview")
    azure_openai_deployment_name: str = Field(default="")

    # FastAPI
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8005)
    api_reload: bool = Field(default=True)

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

    # Business Configuration (loaded from database/YAML, not hardcoded)
    business_hours: dict[str, dict[str, str]] = Field(default_factory=dict)

    # Booking Configuration (loaded from database/YAML)
    booking_advance_days: int = Field(default=14, gt=0)
    cancellation_notice_hours: int = Field(default=24, gt=0)
    same_day_booking_cutoff_hour: int = Field(default=14, ge=0, le=23)

    # Logging
    log_level: str = Field(default="INFO")

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
