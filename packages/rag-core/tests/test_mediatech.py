"""Tests for MediaTech collection catalog."""

from rag_core.mediatech import MEDIATECH_CATALOG


def test_catalog_is_not_empty():
    """Catalog should contain known MediaTech datasets."""
    assert len(MEDIATECH_CATALOG) > 0


def test_known_collections_present():
    """Key MediaTech collections should be in the catalog."""
    expected = {"legi", "service-public", "travail-emploi", "constit", "cnil"}
    assert expected.issubset(MEDIATECH_CATALOG.keys())


def test_entries_have_required_fields():
    """Each entry should have description and presets."""
    for name, entry in MEDIATECH_CATALOG.items():
        assert "description" in entry, f"{name} missing description"
        assert "presets" in entry, f"{name} missing presets"
        assert isinstance(entry["presets"], list), f"{name} presets should be a list"
        assert len(entry["description"]) > 0, f"{name} has empty description"


def test_preset_values_are_valid():
    """Preset references should be valid preset names."""
    valid_presets = {"fast", "balanced", "accurate", "legal", "hr"}
    for name, entry in MEDIATECH_CATALOG.items():
        for preset in entry["presets"]:
            assert preset in valid_presets, f"{name} has invalid preset: {preset}"
