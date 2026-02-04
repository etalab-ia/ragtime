"""Data Foundry providers for synthetic Q/A generation.

This module defines the provider protocol and factory function for
creating data foundry providers (Letta, Albert API, etc.).
"""

from typing import Iterator, Protocol

from .schema import GeneratedSample


class DataFoundryProvider(Protocol):
    """Protocol for data foundry providers.

    Providers handle document upload, agent communication, and Q/A generation.
    """

    def upload_documents(self, document_paths: list[str]) -> None:
        """Upload documents to the provider's storage.

        Args:
            document_paths: List of paths to documents (PDF, MD, TXT)
        """
        ...

    def generate(self, num_samples: int) -> Iterator[GeneratedSample]:
        """Generate Q/A samples from uploaded documents.

        Args:
            num_samples: Target number of samples to generate

        Yields:
            GeneratedSample objects as they are generated
        """
        ...

    def cleanup(self) -> None:
        """Clean up resources (optional).

        Called after generation completes. Providers can use this to
        detach folders, close connections, etc.
        """
        ...


def get_provider(provider_name: str, **kwargs) -> DataFoundryProvider:
    """Factory function to get a data foundry provider.

    Args:
        provider_name: Name of the provider ("letta", "albert")
        **kwargs: Provider-specific configuration

    Returns:
        A DataFoundryProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    if provider_name == "letta":
        from .letta import LettaProvider

        return LettaProvider(**kwargs)
    # Future: add "albert" provider here
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
