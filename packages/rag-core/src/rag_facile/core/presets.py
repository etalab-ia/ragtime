"""Preset management for RAG configurations.

This module provides functions to list, load, and apply configuration presets.
Presets are pre-configured settings optimized for specific use cases:

- fast: Speed-optimized (smaller models, skip reranking)
- balanced: Recommended default (quality/speed tradeoff)
- accurate: Quality-optimized (larger models, hallucination detection)
- legal: Legal documents (strict citations, accuracy validation)
- hr: HR policies (privacy-aware, clear attribution)
"""

from pathlib import Path
from typing import Any

from .loader import load_config, save_config
from .schema import RAGConfig


def _get_preset_dir() -> Path:
    """Get the presets directory path.

    Presets live at ``packages/rag-core/presets/`` in the monorepo but are
    *copied* (not symlinked) into the wheel/editable install because they sit
    outside ``src/``.  To avoid silently serving stale preset files during
    development, we search the CWD ancestor tree for the workspace source
    first, and only fall back to the bundled copy for installed deployments.

    Returns:
        Path to presets directory (source tree or bundled)
    """
    # Dev / workspace mode: walk up from CWD to find the monorepo source.
    # Takes priority so edits to preset TOML files are picked up immediately
    # without needing `uv sync --reinstall-package rag-core`.
    current = Path.cwd().resolve()
    while True:
        candidate = current / "packages" / "rag-core" / "presets"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Installed package (end-user deployment): use the copy bundled in the wheel.
    bundled = Path(__file__).parent / "presets"
    if bundled.exists():
        return bundled

    raise FileNotFoundError("Presets directory not found")


def list_presets() -> list[str]:
    """List available configuration presets.

    Returns:
        List of preset names

    Example:
        >>> presets = list_presets()
        >>> print(presets)
        ['fast', 'balanced', 'accurate', 'legal', 'hr']
    """
    preset_dir = _get_preset_dir()
    return sorted([p.stem for p in preset_dir.glob("*.toml")])


def load_preset(name: str) -> RAGConfig:
    """Load a configuration preset.

    Args:
        name: Preset name (fast, balanced, accurate, legal, hr)

    Returns:
        RAGConfig instance with preset values

    Raises:
        ValueError: If preset doesn't exist

    Example:
        >>> config = load_preset("legal")
        >>> print(config.hallucination.enabled)
        True
    """
    preset_dir = _get_preset_dir()
    preset_path = preset_dir / f"{name}.toml"

    if not preset_path.exists():
        available = ", ".join(list_presets())
        raise ValueError(f"Unknown preset: {name}. Available presets: {available}")

    return load_config(preset_path)


def apply_preset(name: str, target_path: Path | str = "ragfacile.toml") -> None:
    """Apply a preset to workspace configuration file.

    This overwrites the target configuration file with preset values.

    Args:
        name: Preset name
        target_path: Output path for configuration file

    Raises:
        ValueError: If preset doesn't exist

    Example:
        >>> apply_preset("legal", "ragfacile.toml")
        >>> # ragfacile.toml now contains legal preset settings
    """
    config = load_preset(name)
    save_config(config, target_path)


def get_preset_description(name: str) -> str:
    """Get human-readable description of a preset.

    Args:
        name: Preset name

    Returns:
        Description string

    Example:
        >>> print(get_preset_description("legal"))
        'Legal documents - Strict citations, accuracy validation, lower temperature'
    """
    descriptions = {
        "fast": "Speed-optimized - Smaller models, skip reranking",
        "balanced": "Recommended default - Good quality/speed tradeoff",
        "accurate": "Quality-optimized - Larger models, hallucination detection",
        "legal": "Legal documents - Strict citations, accuracy validation, lower temperature",
        "hr": "HR policies - Privacy-aware, clear attribution, semantic search",
    }
    return descriptions.get(name, "Unknown preset")


def compare_presets(name1: str, name2: str) -> dict[str, tuple[Any, Any]]:
    """Compare two presets and show differences.

    Args:
        name1: First preset name
        name2: Second preset name

    Returns:
        Dictionary of differences: {field_path: (value1, value2)}

    Example:
        >>> diffs = compare_presets("fast", "accurate")
        >>> for field, (val1, val2) in diffs.items():
        ...     print(f"{field}: {val1} -> {val2}")
        generation.model: openweight-small -> openweight-large
        reranking.enabled: False -> True
    """
    config1 = load_preset(name1)
    config2 = load_preset(name2)

    dict1 = config1.model_dump()
    dict2 = config2.model_dump()

    differences: dict[str, tuple[Any, Any]] = {}

    def _compare_dicts(d1: dict, d2: dict, prefix: str = "") -> None:
        """Recursively compare nested dictionaries."""
        # Use union of keys to catch differences in both directions
        for key in sorted(d1.keys() | d2.keys()):
            path = f"{prefix}.{key}" if prefix else key
            val1 = d1.get(key)
            val2 = d2.get(key)

            # Skip if values are identical
            if val1 == val2:
                continue

            # Recurse for nested dictionaries
            if isinstance(val1, dict) and isinstance(val2, dict):
                _compare_dicts(val1, val2, path)
            else:
                differences[path] = (val1, val2)

    _compare_dicts(dict1, dict2)
    return differences
