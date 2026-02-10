"""Tests for BaseModel and response types."""

import json

import pytest
from pydantic import ValidationError

from albert._models import BaseModel


class SampleModel(BaseModel):
    """Sample model for testing."""

    name: str
    score: float
    metadata: dict = {}


class TestBaseModel:
    """Test BaseModel helper methods."""

    def test_to_dict(self):
        """Test to_dict() method."""
        model = SampleModel(name="test", score=0.95, metadata={"key": "value"})
        result = model.to_dict()

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["score"] == 0.95
        assert result["metadata"] == {"key": "value"}

    def test_to_json(self):
        """Test to_json() method."""
        model = SampleModel(name="test", score=0.95)
        result = model.to_json()

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["score"] == 0.95

    def test_pydantic_validation(self):
        """Test that Pydantic validation works."""
        # Valid model
        model = SampleModel(name="test", score=0.95)
        assert model.name == "test"

        # Invalid score type
        with pytest.raises(ValidationError):
            SampleModel(name="test", score="not_a_float")  # type: ignore[arg-type]

    def test_extra_fields_allowed(self):
        """Test that extra fields from API are allowed."""
        # This is important for forward compatibility
        model = SampleModel(
            name="test",
            score=0.95,
            extra_field="should_not_fail",  # type: ignore[call-arg]
        )
        assert model.name == "test"
        assert model.score == 0.95

    def test_default_values(self):
        """Test default values work."""
        model = SampleModel(name="test", score=0.95)
        assert model.metadata == {}  # Default value

    def test_dict_roundtrip(self):
        """Test serialization roundtrip."""
        original = SampleModel(name="test", score=0.95, metadata={"key": "value"})

        # to_dict -> create new model
        dict_data = original.to_dict()
        restored = SampleModel(**dict_data)

        assert restored.name == original.name
        assert restored.score == original.score
        assert restored.metadata == original.metadata

    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = SampleModel(name="test", score=0.95, metadata={"key": "value"})

        # to_json -> parse -> create new model
        json_data = original.to_json()
        parsed_dict = json.loads(json_data)
        restored = SampleModel(**parsed_dict)

        assert restored.name == original.name
        assert restored.score == original.score
        assert restored.metadata == original.metadata
