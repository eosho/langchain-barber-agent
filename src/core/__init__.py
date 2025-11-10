"""Core package initialization.

This package contains core functionality shared across the application,
including configuration, database connections, logging, and exceptions.
"""

from src.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
