"""LLM registry for managing different language model providers.

Provides centralized configuration and initialization for OpenAI and Azure OpenAI models.
"""

from functools import lru_cache

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from src.core.config import get_settings


class LLMRegistry:
    """Registry for managing LLM providers.

    Supports OpenAI and Azure OpenAI with configuration-based initialization.
    """

    def __init__(self) -> None:
        """Initialize the LLM registry with application settings."""
        self.settings = get_settings()

    def create_openai(self) -> ChatOpenAI:
        """Create an OpenAI chat model instance.

        Returns:
            Configured ChatOpenAI instance.

        Raises:
            ValueError: If OpenAI API key is not configured.
        """
        if not self.settings.openai_api_key:
            raise ValueError(
                "OpenAI API key not configured. " "Set OPENAI_API_KEY environment variable."
            )

        return ChatOpenAI(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
        )

    def create_azure_openai(self) -> AzureChatOpenAI:
        """Create an Azure OpenAI chat model instance.

        Returns:
            Configured AzureChatOpenAI instance.

        Raises:
            ValueError: If Azure OpenAI configuration is incomplete.
        """
        if not all(
            [
                self.settings.azure_openai_api_key,
                self.settings.azure_openai_endpoint,
                self.settings.azure_openai_deployment_name,
            ]
        ):
            raise ValueError(
                "Azure OpenAI configuration incomplete. "
                "Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
                "and AZURE_OPENAI_DEPLOYMENT_NAME environment variables."
            )

        return AzureChatOpenAI(
            model=self.settings.openai_model,
            azure_deployment=self.settings.azure_openai_deployment_name,
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            temperature=self.settings.openai_temperature,
        )

    def get_model(self, provider: str | None = None) -> ChatOpenAI | AzureChatOpenAI:
        """Get a configured LLM instance based on provider.

        Args:
            provider: LLM provider ("openai" or "azure_openai").
                     If None, uses settings.llm_provider.

        Returns:
            Configured chat model instance.

        Raises:
            ValueError: If provider is not supported.
        """
        provider = provider or self.settings.llm_provider

        if provider == "openai":
            return self.create_openai()
        elif provider == "azure_openai":
            return self.create_azure_openai()
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. " "Use 'openai' or 'azure_openai'."
            )


@lru_cache(maxsize=1)
def get_llm_registry() -> LLMRegistry:
    """Get a singleton LLM registry instance.

    Returns:
        Cached LLMRegistry instance.
    """
    return LLMRegistry()


def get_llm(provider: str | None = None) -> ChatOpenAI | AzureChatOpenAI:
    """Convenience function to get a configured LLM.

    Args:
        provider: LLM provider ("openai" or "azure_openai").
                 If None, uses settings.llm_provider.

    Returns:
        Configured chat model instance.
    """
    registry = get_llm_registry()
    return registry.get_model(provider)
