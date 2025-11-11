"""Version information for the barbershop booking agent.

Version is read from pyproject.toml to maintain a single source of truth.
"""

import tomllib
from pathlib import Path


def get_version() -> str:
    """Get version from pyproject.toml.

    Returns:
        Version string (e.g., "0.1.1").

    Raises:
        FileNotFoundError: If pyproject.toml not found.
        KeyError: If version key not found in pyproject.toml.
    """
    # Navigate from src/__version__.py -> src/ -> project_root/
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["version"]


__version__ = get_version()

