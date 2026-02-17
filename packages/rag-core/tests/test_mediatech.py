"""Tests for MediaTech collection catalog."""

from rag_facile.core.mediatech import MEDIATECH_CATALOG


def test_catalog_is_not_empty():
    """Catalog should contain known MediaTech datasets."""
    assert len(MEDIATECH_CATALOG) > 0


def test_known_collections_present():
    """Key MediaTech collections should be in the catalog."""
    expected = {"service-public", "travail-emploi", "annuaire-administrations-etat"}
    assert expected.issubset(MEDIATECH_CATALOG.keys())


def test_entries_have_required_fields():
    """Each entry should have id, description, and presets."""
    for name, entry in MEDIATECH_CATALOG.items():
        assert "id" in entry, f"{name} missing id"
        assert "description" in entry, f"{name} missing description"
        assert "presets" in entry, f"{name} missing presets"
        assert isinstance(entry["id"], int), f"{name} id should be an int"
        assert isinstance(entry["presets"], list), f"{name} presets should be a list"
        assert len(entry["description"]) > 0, f"{name} has empty description"


def test_preset_values_are_valid():
    """Preset references should be valid preset names."""
    valid_presets = {"fast", "balanced", "accurate", "legal", "hr"}
    for name, entry in MEDIATECH_CATALOG.items():
        for preset in entry["presets"]:
            assert preset in valid_presets, f"{name} has invalid preset: {preset}"


def test_known_collection_ids():
    """Known collection IDs should match the etalab Albert API instance."""
    assert MEDIATECH_CATALOG["service-public"]["id"] == 785
    assert MEDIATECH_CATALOG["travail-emploi"]["id"] == 784
    assert MEDIATECH_CATALOG["annuaire-administrations-etat"]["id"] == 783
    assert MEDIATECH_CATALOG["data-gouv-datasets-catalog"]["id"] == 1094
