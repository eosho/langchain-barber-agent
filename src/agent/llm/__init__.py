"""LLM provider management for the booking agent.

This module provides a centralized registry for managing different LLM providers
(OpenAI, Azure OpenAI) with clean configuration and initialization.
"""

from src.agent.llm.registry import LLMRegistry, get_llm, get_llm_registry

__all__ = [
    "LLMRegistry",
    "get_llm",
    "get_llm_registry",
]
