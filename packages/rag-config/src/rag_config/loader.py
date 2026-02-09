"""Configuration loading and saving with environment variable override support.

This module handles loading RAG configurations from TOML files and environment
variables, with a clear precedence order:
1. Environment variables (highest priority)
2. TOML file values
3. Pydantic defaults (fallback)

Environment variable format: RAG_<SECTION>_<KEY>
Example: RAG_GENERATION_MODEL=openweight-large
"""

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from .schema import RAGConfig


def parse_value(value: str) -> Any:
    """Parse string value to appropriate Python type.

    Handles boolean, integer, float, and string types with smart detection.
    Used for both environment variable overrides and CLI value parsing.

    Args:
        value: Raw string value to parse

    Returns:
        Parsed value (bool, int, float, or string)

    Examples:
        >>> parse_value("true")
        True
        >>> parse_value("42")
        42
        >>> parse_value("3.14")
        3.14
        >>> parse_value("openweight-large")
        'openweight-large'
    """
    # Boolean
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False

    # Try numeric types
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # String (default)
    return value


def _apply_env_overrides(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to config dictionary.

    Environment variables follow the pattern: RAG_<SECTION>_<KEY>
    Example: RAG_GENERATION_MODEL overrides config["generation"]["model"]

    Args:
        config_dict: Configuration dictionary from TOML file

    Returns:
        Updated configuration dictionary with env var overrides applied
    """
    prefix = "RAG_"

    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue

        # Remove prefix and split into parts
        key_parts = env_key[len(prefix) :].lower().split("_")

        if len(key_parts) < 2:
            continue  # Invalid format, skip

        section = key_parts[0]
        field = "_".join(key_parts[1:])  # Rejoin in case of multi-part field names

        # Apply override (ensure section exists)
        section_dict = config_dict.setdefault(section, {})
        if isinstance(section_dict, dict):
            section_dict[field] = parse_value(env_value)
        else:
            # Top-level field
            config_dict[section] = parse_value(env_value)

    return config_dict


def load_config(path: Path | str = "ragfacile.toml") -> RAGConfig:
    """Load and validate RAG configuration from TOML file.

    Supports environment variable overrides using RAG_<SECTION>_<KEY> format.

    Args:
        path: Path to TOML configuration file (default: ragfacile.toml)

    Returns:
        Validated RAGConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValidationError: If config is invalid

    Example:
        >>> config = load_config()
        >>> print(config.generation.model)
        'openweight-medium'

        >>> # With env var override
        >>> os.environ["RAG_GENERATION_MODEL"] = "openweight-large"
        >>> config = load_config()
        >>> print(config.generation.model)
        'openweight-large'
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    # Load TOML file
    with open(path, "rb") as f:
        config_dict = tomllib.load(f)

    # Apply environment variable overrides
    config_dict = _apply_env_overrides(config_dict)

    # Validate and return
    return RAGConfig(**config_dict)


def load_config_or_default(path: Path | str = "ragfacile.toml") -> RAGConfig:
    """Load configuration, or return default if file doesn't exist.

    This is useful for applications that want to work with default config
    when no ragfacile.toml is present.

    Args:
        path: Path to TOML configuration file

    Returns:
        RAGConfig instance (loaded or default)
    """
    path = Path(path)

    if not path.exists():
        # Return default config with env var overrides
        return RAGConfig(**_apply_env_overrides({}))

    return load_config(path)


def save_config(config: RAGConfig, path: Path | str = "ragfacile.toml") -> None:
    """Save RAG configuration to TOML file.

    Args:
        config: RAGConfig instance to save
        path: Output path for TOML file

    Example:
        >>> config = load_config()
        >>> config.generation.temperature = 0.5
        >>> save_config(config, "ragfacile.toml")
    """
    path = Path(path)

    # Convert to dict and write
    config_dict = config.model_dump()

    with open(path, "wb") as f:
        tomli_w.dump(config_dict, f)


def validate_config(path: Path | str = "ragfacile.toml") -> RAGConfig:
    """Validate a configuration file without side effects.

    Args:
        path: Path to TOML configuration file

    Returns:
        Validated RAGConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValidationError: If config is invalid

    Example:
        >>> from pydantic import ValidationError
        >>> try:
        ...     config = validate_config("ragfacile.toml")
        ...     print("✓ Configuration is valid")
        ... except ValidationError as e:
        ...     print(f"✗ Configuration errors: {e}")
    """
    return load_config(path)


def export_json_schema() -> str:
    """Export JSON Schema for ragfacile.toml configuration.

    This schema can be used for:
    - IDE autocomplete and validation
    - Documentation generation
    - Schema validation tools

    Returns:
        JSON Schema as string

    Example:
        >>> schema = export_json_schema()
        >>> with open("ragfacile-schema.json", "w") as f:
        ...     f.write(schema)
    """
    import json

    schema = RAGConfig.model_json_schema()
    return json.dumps(schema, indent=2)


def get_env_override_docs() -> str:
    """Generate documentation for environment variable overrides.

    Returns:
        Markdown-formatted documentation string

    Example:
        >>> print(get_env_override_docs())
    """
    sections = [
        ("eval", ["provider", "target_samples"]),
        ("embedding", ["model", "batch_size"]),
        ("retrieval", ["method", "top_k", "score_threshold"]),
        ("reranking", ["enabled", "model", "top_n"]),
        ("generation", ["model", "temperature", "max_tokens"]),
        ("hallucination", ["enabled", "method"]),
    ]

    docs = ["# Environment Variable Overrides\n"]
    docs.append("Override any config value using environment variables:\n")
    docs.append("Format: `RAG_<SECTION>_<KEY>=<value>`\n")
    docs.append("\n## Examples\n")

    for section, keys in sections:
        docs.append(f"\n### {section.title()}\n")
        for key in keys:
            env_var = f"RAG_{section.upper()}_{key.upper()}"
            docs.append(f"- `{env_var}` - Override `{section}.{key}`\n")

    docs.append("\n## Usage\n")
    docs.append("```bash\n")
    docs.append("# Example: Use large model for this run\n")
    docs.append("export RAG_GENERATION_MODEL=openweight-large\n")
    docs.append("export RAG_RETRIEVAL_TOP_K=20\n")
    docs.append("python app.py\n")
    docs.append("```\n")

    return "".join(docs)
