"""Base models for Albert API responses.

Follows OpenAI SDK pattern of extending Pydantic with helper methods.
"""

from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    """Base model for all Albert API response types.

    Provides helper methods matching OpenAI SDK patterns:
    - to_dict(): Convert to dictionary
    - to_json(): Convert to JSON string
    """

    model_config = ConfigDict(
        # Allow extra fields from API (forward compatibility)
        extra="allow",
        # Use attribute names as-is (no camelCase conversion)
        populate_by_name=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of the model.
        """
        return self.model_dump()

    def to_json(self) -> str:
        """Convert model to JSON string.

        Returns:
            JSON string representation of the model.
        """
        return self.model_dump_json()
