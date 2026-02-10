"""Tests for configuration presets."""

from pathlib import Path

import pytest

from config.presets import (
    apply_preset,
    compare_presets,
    get_preset_description,
    list_presets,
    load_preset,
)


def test_list_presets():
    """Test listing available presets."""
    presets = list_presets()

    assert isinstance(presets, list)
    assert len(presets) >= 5
    assert "fast" in presets
    assert "balanced" in presets
    assert "accurate" in presets
    assert "legal" in presets
    assert "hr" in presets


def test_load_balanced_preset():
    """Test loading balanced preset."""
    config = load_preset("balanced")

    assert config.meta.preset == "balanced"
    assert config.generation.model == "openweight-medium"
    assert config.retrieval.method == "hybrid"
    assert config.reranking.enabled is True


def test_load_fast_preset():
    """Test loading fast preset."""
    config = load_preset("fast")

    assert config.meta.preset == "fast"
    assert config.generation.model == "openweight-small"
    assert config.reranking.enabled is False
    assert config.retrieval.top_k == 5


def test_load_accurate_preset():
    """Test loading accurate preset."""
    config = load_preset("accurate")

    assert config.meta.preset == "accurate"
    assert config.generation.model == "openweight-large"
    assert config.hallucination.enabled is True
    assert config.retrieval.top_k == 20


def test_load_legal_preset():
    """Test loading legal preset."""
    config = load_preset("legal")

    assert config.meta.preset == "legal"
    assert config.generation.model == "openweight-large"
    assert config.generation.temperature == 0.3  # Low for legal
    assert config.hallucination.enabled is True
    assert config.hallucination.threshold == 0.95  # Very strict
    assert config.hallucination.fallback == "reject"
    assert config.context.formatting.citation_style == "footnote"


def test_load_hr_preset():
    """Test loading hr preset."""
    config = load_preset("hr")

    assert config.meta.preset == "hr"
    assert config.generation.model == "openweight-medium"
    assert config.retrieval.hybrid.alpha == 0.7  # Semantic-weighted
    assert config.hallucination.enabled is True


def test_load_invalid_preset_raises_error():
    """Test that loading invalid preset raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        load_preset("nonexistent")

    assert "Unknown preset" in str(exc_info.value)
    assert "nonexistent" in str(exc_info.value)


def test_apply_preset(tmp_path: Path):
    """Test applying preset to configuration file."""
    config_file = tmp_path / "ragfacile.toml"

    # Apply preset
    apply_preset("accurate", config_file)

    # Verify file exists and has correct values
    assert config_file.exists()

    # Load and verify
    from config import load_config

    config = load_config(config_file)
    assert config.meta.preset == "accurate"
    assert config.generation.model == "openweight-large"


def test_get_preset_description():
    """Test getting preset descriptions."""
    desc = get_preset_description("legal")

    assert isinstance(desc, str)
    assert len(desc) > 0
    assert "legal" in desc.lower() or "citation" in desc.lower()


def test_get_preset_description_for_all_presets():
    """Test descriptions exist for all presets."""
    presets = list_presets()

    for preset in presets:
        desc = get_preset_description(preset)
        assert isinstance(desc, str)
        assert len(desc) > 0


def test_compare_presets():
    """Test comparing two presets."""
    differences = compare_presets("fast", "accurate")

    assert isinstance(differences, dict)
    assert len(differences) > 0

    # Should show model difference
    assert any("generation.model" in key for key in differences.keys())

    # Should show reranking difference
    assert any("reranking.enabled" in key for key in differences.keys())


def test_compare_identical_presets():
    """Test comparing preset with itself returns no differences."""
    differences = compare_presets("balanced", "balanced")

    assert isinstance(differences, dict)
    assert len(differences) == 0


def test_presets_have_consistent_structure():
    """Test that all presets have the same structure."""
    presets = list_presets()
    configs = [load_preset(p) for p in presets]

    # All should have the same top-level keys
    first_keys = set(configs[0].model_dump().keys())

    for config in configs[1:]:
        assert set(config.model_dump().keys()) == first_keys


def test_presets_are_valid():
    """Test that all presets are valid configurations."""
    presets = list_presets()

    for preset in presets:
        config = load_preset(preset)
        assert config.meta.preset == preset
        assert config.meta.schema_version == "1.0.0"
