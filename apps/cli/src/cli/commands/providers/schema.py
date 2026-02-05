"""Schema definitions for Data Foundry output.

Defines the Ragas-compatible output format for generated Q/A samples.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SampleMetadata:
    """Metadata for a generated sample."""

    source_file: str = ""
    quality_score: float = 0.0
    topic_summary: str = ""
    # Extensible for additional metadata
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding empty extra."""
        result = {
            "source_file": self.source_file,
            "quality_score": self.quality_score,
            "topic_summary": self.topic_summary,
        }
        if self.extra:
            result.update(self.extra)
        return result


@dataclass
class GeneratedSample:
    """A generated Q/A sample in Ragas-compatible format.

    Attributes:
        user_input: The question in French
        retrieved_contexts: List of context passages
        reference: The ground truth answer in French
        metadata: Additional metadata about the sample
    """

    user_input: str
    retrieved_contexts: list[str]
    reference: str
    metadata: SampleMetadata = field(default_factory=SampleMetadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert to Ragas-compatible dictionary format."""
        return {
            "user_input": self.user_input,
            "retrieved_contexts": self.retrieved_contexts,
            "reference": self.reference,
            "_metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeneratedSample":
        """Create from dictionary (e.g., parsed JSON)."""
        metadata_dict = data.get("_metadata", {})
        metadata = SampleMetadata(
            source_file=metadata_dict.get("source_file", ""),
            quality_score=metadata_dict.get("quality_score", 0.0),
            topic_summary=metadata_dict.get("topic_summary", ""),
        )
        return cls(
            user_input=data.get("user_input", ""),
            retrieved_contexts=data.get("retrieved_contexts", []),
            reference=data.get("reference", ""),
            metadata=metadata,
        )
