"""Tests for configuration loading and environment variable overrides."""

from pathlib import Path

import pytest

from config.loader import (
    export_json_schema,
    load_config,
    load_config_or_default,
    save_config,
)
from config.schema import RAGConfig


def test_load_nonexistent_file_raises_error():
    """Test that loading nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.toml")


def test_load_config_or_default_with_nonexistent_file():
    """Test loading default config when file doesn't exist."""
    config = load_config_or_default("nonexistent.toml")
    assert isinstance(config, RAGConfig)
    assert config.generation.model == "openweight-medium"


def test_save_and_load_config(tmp_path: Path):
    """Test saving and loading configuration."""
    config_file = tmp_path / "test_config.toml"

    # Create and save config
    config = RAGConfig()
    config.generation.model = "openweight-large"
    config.generation.temperature = 0.5
    save_config(config, config_file)

    # Load and verify
    loaded_config = load_config(config_file)
    assert loaded_config.generation.model == "openweight-large"
    assert loaded_config.generation.temperature == 0.5


def test_env_var_override_generation_model(tmp_path: Path, monkeypatch):
    """Test environment variable override for generation.model."""
    config_file = tmp_path / "test_config.toml"

    # Save default config
    config = RAGConfig()
    save_config(config, config_file)

    # Set env var
    monkeypatch.setenv("RAG_GENERATION_MODEL", "openweight-large")

    # Load - should use env var value
    loaded_config = load_config(config_file)
    assert loaded_config.generation.model == "openweight-large"


def test_env_var_override_multiple_values(tmp_path: Path, monkeypatch):
    """Test multiple environment variable overrides."""
    config_file = tmp_path / "test_config.toml"

    # Save default config
    config = RAGConfig()
    save_config(config, config_file)

    # Set multiple env vars
    monkeypatch.setenv("RAG_GENERATION_MODEL", "openweight-small")
    monkeypatch.setenv("RAG_GENERATION_TEMPERATURE", "0.3")
    monkeypatch.setenv("RAG_RETRIEVAL_TOP_K", "20")
    monkeypatch.setenv("RAG_RERANKING_ENABLED", "false")

    # Load and verify
    loaded_config = load_config(config_file)
    assert loaded_config.generation.model == "openweight-small"
    assert loaded_config.generation.temperature == 0.3
    assert loaded_config.retrieval.top_k == 20
    assert loaded_config.reranking.enabled is False


def test_env_var_boolean_parsing(tmp_path: Path, monkeypatch):
    """Test boolean environment variable parsing."""
    config_file = tmp_path / "test_config.toml"
    config = RAGConfig()
    save_config(config, config_file)

    # Test various boolean formats
    test_cases = [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("no", False),
        ("0", False),
    ]

    for env_value, expected in test_cases:
        monkeypatch.setenv("RAG_RERANKING_ENABLED", env_value)
        loaded_config = load_config(config_file)
        assert loaded_config.reranking.enabled is expected, (
            f"Failed for env_value={env_value}"
        )


def test_env_var_numeric_parsing(tmp_path: Path, monkeypatch):
    """Test numeric environment variable parsing."""
    config_file = tmp_path / "test_config.toml"
    config = RAGConfig()
    save_config(config, config_file)

    # Integer
    monkeypatch.setenv("RAG_RETRIEVAL_TOP_K", "15")
    loaded_config = load_config(config_file)
    assert loaded_config.retrieval.top_k == 15
    assert isinstance(loaded_config.retrieval.top_k, int)

    # Float
    monkeypatch.setenv("RAG_GENERATION_TEMPERATURE", "0.8")
    loaded_config = load_config(config_file)
    assert loaded_config.generation.temperature == 0.8
    assert isinstance(loaded_config.generation.temperature, float)


def test_env_var_does_not_affect_unset_values(tmp_path: Path, monkeypatch):
    """Test that env vars only override explicitly set values."""
    config_file = tmp_path / "test_config.toml"
    config = RAGConfig()
    save_config(config, config_file)

    # Set only one env var
    monkeypatch.setenv("RAG_GENERATION_MODEL", "openweight-large")

    loaded_config = load_config(config_file)
    # Overridden value
    assert loaded_config.generation.model == "openweight-large"
    # Other values remain default
    assert loaded_config.generation.temperature == 0.7
    assert loaded_config.retrieval.top_k == 10


def test_export_json_schema():
    """Test JSON Schema export."""
    schema = export_json_schema()

    assert isinstance(schema, str)
    assert "RAGConfig" in schema or "properties" in schema
    assert "generation" in schema
    assert "retrieval" in schema


def test_config_with_comments_preserved(tmp_path: Path):
    """Test that TOML comments are handled correctly."""
    config_file = tmp_path / "test_config.toml"

    # Write config with comments manually
    with open(config_file, "w") as f:
        f.write("""# Test configuration
[generation]
model = "openweight-medium"  # Default model
temperature = 0.7

[retrieval]
method = "hybrid"
top_k = 10
""")

    # Load - should work despite comments
    config = load_config(config_file)
    assert config.generation.model == "openweight-medium"
    assert config.retrieval.method == "hybrid"
