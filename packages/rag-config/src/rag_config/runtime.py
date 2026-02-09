"""Runtime configuration management for applications.

This module provides a singleton pattern for accessing configuration
throughout an application's lifecycle. The config is loaded once and
cached for performance.
"""

from functools import lru_cache
from pathlib import Path

from .loader import load_config_or_default
from .schema import RAGConfig


@lru_cache(maxsize=1)
def get_config(path: Path | str = "ragfacile.toml") -> RAGConfig:
    """Get cached RAG configuration (singleton pattern).

    The configuration is loaded once and cached. Subsequent calls return
    the same instance without re-reading the file.

    Args:
        path: Path to configuration file (default: ragfacile.toml)

    Returns:
        RAGConfig instance

    Example:
        >>> # First call loads from file
        >>> config = get_config()
        >>> print(config.generation.model)
        'openweight-medium'
        >>>
        >>> # Subsequent calls return cached instance
        >>> config2 = get_config()
        >>> assert config is config2  # Same object
    """
    return load_config_or_default(path)


def reload_config(path: Path | str = "ragfacile.toml") -> RAGConfig:
    """Clear cache and reload configuration.

    Use this when configuration has changed and needs to be reloaded
    during application runtime.

    Args:
        path: Path to configuration file

    Returns:
        Newly loaded RAGConfig instance

    Example:
        >>> config = get_config()
        >>> # ... user edits ragfacile.toml ...
        >>> config = reload_config()  # Load fresh config
    """
    get_config.cache_clear()
    return get_config(path)


def has_config_file(path: Path | str = "ragfacile.toml") -> bool:
    """Check if configuration file exists.

    Args:
        path: Path to configuration file

    Returns:
        True if file exists, False otherwise

    Example:
        >>> if has_config_file():
        ...     config = get_config()
        ... else:
        ...     print("Using default configuration")
    """
    return Path(path).exists()
