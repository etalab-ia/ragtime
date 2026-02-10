"""Tests for runtime configuration management."""

from pathlib import Path

from config.runtime import get_config, has_config_file, reload_config
from config.schema import RAGConfig


def test_get_config_returns_config():
    """Test that get_config returns valid RAGConfig."""
    config = get_config("nonexistent.toml")  # Uses default

    assert isinstance(config, RAGConfig)
    assert config.generation.model == "openweight-medium"


def test_get_config_caching():
    """Test that get_config returns cached instance."""
    config1 = get_config("nonexistent.toml")
    config2 = get_config("nonexistent.toml")

    # Should be the exact same object (singleton)
    assert config1 is config2


def test_reload_config_clears_cache(tmp_path: Path):
    """Test that reload_config clears cache."""
    from config import save_config

    config_file = tmp_path / "test_config.toml"

    # Create initial config
    config = RAGConfig()
    config.generation.model = "openweight-small"
    save_config(config, config_file)

    # Load (cached)
    config1 = get_config(str(config_file))
    assert config1.generation.model == "openweight-small"

    # Modify file
    config.generation.model = "openweight-large"
    save_config(config, config_file)

    # Without reload, should get cached version
    config2 = get_config(str(config_file))
    assert config2.generation.model == "openweight-small"  # Still cached
    assert config2 is config1  # Same object

    # After reload, should get new version
    config3 = reload_config(str(config_file))
    assert config3.generation.model == "openweight-large"
    assert config3 is not config1  # Different object


def test_has_config_file(tmp_path: Path):
    """Test checking if config file exists."""
    config_file = tmp_path / "ragfacile.toml"

    # File doesn't exist yet
    assert not has_config_file(str(config_file))

    # Create file
    config_file.touch()

    # File now exists
    assert has_config_file(str(config_file))


def test_get_config_with_env_override(tmp_path: Path, monkeypatch):
    """Test that get_config respects env var overrides."""
    from config import save_config

    config_file = tmp_path / "test_config.toml"

    # Save default config
    config = RAGConfig()
    save_config(config, config_file)

    # Set env var
    monkeypatch.setenv("RAG_GENERATION_MODEL", "openweight-large")

    # Clear cache to force reload
    get_config.cache_clear()

    # Load - should use env var
    loaded_config = get_config(str(config_file))
    assert loaded_config.generation.model == "openweight-large"
