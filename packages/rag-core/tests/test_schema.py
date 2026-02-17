"""Tests for configuration schema validation."""

import pytest
from pydantic import ValidationError

from rag_facile.core.schema import (
    ChunkingConfig,
    EmbeddingConfig,
    GenerationConfig,
    RAGConfig,
    RetrievalConfig,
    StorageConfig,
)


def test_default_config_is_valid():
    """Test that default configuration is valid."""
    config = RAGConfig()
    assert config.meta.schema_version == "1.0.0"
    assert config.meta.preset == "balanced"
    assert config.generation.model == "openweight-medium"


def test_embedding_config_validation():
    """Test embedding configuration validation."""
    # Valid config
    config = EmbeddingConfig(model="openweight-embeddings", batch_size=16)
    assert config.model == "openweight-embeddings"
    assert config.batch_size == 16

    # Invalid batch_size (too large)
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingConfig(batch_size=200)
    assert "batch_size" in str(exc_info.value)


def test_retrieval_config_validation():
    """Test retrieval configuration validation."""
    # Valid config
    config = RetrievalConfig(strategy="hybrid", top_k=10)
    assert config.strategy == "hybrid"
    assert config.hybrid.alpha == 0.5  # Default

    # Invalid strategy
    with pytest.raises(ValidationError) as exc_info:
        RetrievalConfig(strategy="invalid")  # type: ignore[arg-type]
    assert "strategy" in str(exc_info.value)

    # Invalid top_k (too large)
    with pytest.raises(ValidationError) as exc_info:
        RetrievalConfig(top_k=200)
    assert "top_k" in str(exc_info.value)


def test_generation_config_validation():
    """Test generation configuration validation."""
    # Valid config
    config = GenerationConfig(
        model="openweight-large",
        temperature=0.5,
        max_tokens=2048,
    )
    assert config.model == "openweight-large"
    assert config.temperature == 0.5

    # Invalid temperature (too high)
    with pytest.raises(ValidationError) as exc_info:
        GenerationConfig(temperature=3.0)
    assert "temperature" in str(exc_info.value)


def test_chunking_config_validation():
    """Test chunking configuration validation."""
    # Valid config
    config = ChunkingConfig(
        strategy="semantic",
        chunk_size=512,
        chunk_overlap=50,
    )
    assert config.strategy == "semantic"
    assert config.chunk_size == 512

    # Invalid strategy
    with pytest.raises(ValidationError) as exc_info:
        ChunkingConfig(strategy="invalid")  # type: ignore[arg-type]
    assert "strategy" in str(exc_info.value)


def test_nested_config_validation():
    """Test nested configuration sections."""
    config = RAGConfig()

    # Access nested values
    assert config.retrieval.hybrid.alpha == 0.5
    assert config.formatting.citations.enabled is True
    assert config.ingestion.ocr.enabled is True

    # Modify nested values
    config.retrieval.hybrid.alpha = 0.8
    assert config.retrieval.hybrid.alpha == 0.8


def test_config_serialization():
    """Test configuration serialization to dict."""
    config = RAGConfig()
    config_dict = config.model_dump()

    assert isinstance(config_dict, dict)
    assert "meta" in config_dict
    assert "generation" in config_dict
    assert config_dict["generation"]["model"] == "openweight-medium"


def test_config_from_dict():
    """Test configuration creation from dictionary."""
    config_dict = {
        "generation": {
            "model": "openweight-large",
            "temperature": 0.5,
        },
        "retrieval": {
            "strategy": "semantic",
            "top_k": 15,
        },
    }

    config = RAGConfig(**config_dict)  # type: ignore[arg-type]
    assert config.generation.model == "openweight-large"
    assert config.generation.temperature == 0.5
    assert config.retrieval.strategy == "semantic"
    assert config.retrieval.top_k == 15


def test_storage_config_collections_default():
    """Test that storage.collections defaults to empty list."""
    config = StorageConfig()
    assert config.collections == []


def test_storage_config_collections_accepts_list():
    """Test that storage.collections accepts a list of ints."""
    config = StorageConfig(collections=[42, 87, 103])
    assert config.collections == [42, 87, 103]


def test_storage_config_in_rag_config():
    """Test that storage.collections is accessible from RAGConfig."""
    config = RAGConfig()
    assert config.storage.collections == []

    config_with_collections = RAGConfig(storage=StorageConfig(collections=[1, 2, 3]))
    assert config_with_collections.storage.collections == [1, 2, 3]


def test_json_schema_generation():
    """Test that JSON Schema can be generated."""
    schema = RAGConfig.model_json_schema()

    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "generation" in schema["properties"]
    assert "retrieval" in schema["properties"]
