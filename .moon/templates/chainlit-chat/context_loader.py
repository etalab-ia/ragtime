"""Context provider factory - dynamically loads enabled modules.

This module reads modules.yml and loads only the configured context providers.
Users can enable/disable providers by editing modules.yml without regenerating.
"""

import importlib
from pathlib import Path
from typing import Any, Protocol

import yaml


class ContextProvider(Protocol):
    """Protocol for context providers."""

    def __call__(self, path: str | Path, filename: str | None = None) -> str:
        """Process a file and return formatted context."""
        ...


class BytesContextProvider(Protocol):
    """Protocol for context providers that accept bytes."""

    def __call__(self, data: bytes, filename: str) -> str:
        """Process bytes and return formatted context."""
        ...


# Provider registry - maps provider names to their processing functions
_file_processors: dict[str, ContextProvider] = {}
_bytes_processors: dict[str, BytesContextProvider] = {}


def _load_modules_config() -> dict[str, Any]:
    """Load the modules.yml configuration."""
    config_path = Path(__file__).parent / "modules.yml"
    if not config_path.exists():
        return {"context_providers": {}}
    return yaml.safe_load(config_path.read_text()) or {"context_providers": {}}


def _initialize_providers() -> None:
    """Initialize providers from modules.yml configuration."""
    global _file_processors, _bytes_processors

    if _file_processors:  # Already initialized
        return

    config = _load_modules_config()
    providers = config.get("context_providers", {})

    for name, module_name in providers.items():
        try:
            module = importlib.import_module(module_name)

            # Register file processor if available
            if hasattr(module, "process_pdf_file"):
                _file_processors[name] = module.process_pdf_file
            elif hasattr(module, "process_file"):
                _file_processors[name] = module.process_file

            # Register bytes processor if available
            if hasattr(module, "extract_text_from_bytes"):
                # Wrap to include formatting
                if hasattr(module, "format_as_context"):

                    def make_bytes_processor(mod: Any) -> BytesContextProvider:
                        def processor(data: bytes, filename: str) -> str:
                            text = mod.extract_text_from_bytes(data)
                            return mod.format_as_context(text, filename)

                        return processor

                    _bytes_processors[name] = make_bytes_processor(module)

        except ImportError:
            # Module not installed, skip silently
            pass


def get_file_processor(provider: str) -> ContextProvider | None:
    """Get a file processor by provider name.

    Args:
        provider: The provider name (e.g., 'pdf', 'chroma')

    Returns:
        The processor function or None if not available.
    """
    _initialize_providers()
    return _file_processors.get(provider)


def get_bytes_processor(provider: str) -> BytesContextProvider | None:
    """Get a bytes processor by provider name.

    Args:
        provider: The provider name (e.g., 'pdf')

    Returns:
        The processor function or None if not available.
    """
    _initialize_providers()
    return _bytes_processors.get(provider)


def process_file(path: str | Path, filename: str | None = None) -> str:
    """Process a file using the appropriate provider based on extension.

    Args:
        path: Path to the file
        filename: Optional display name

    Returns:
        Formatted context string, or error message if no provider available.
    """
    _initialize_providers()
    path = Path(path)
    ext = path.suffix.lower()

    # Map extensions to providers
    ext_to_provider = {
        ".pdf": "pdf",
    }

    provider = ext_to_provider.get(ext)
    if provider and provider in _file_processors:
        return _file_processors[provider](str(path), filename)

    return f"\n\nUnsupported file type: {ext}\n"


def process_bytes(data: bytes, filename: str) -> str:
    """Process file bytes using the appropriate provider based on filename.

    Args:
        data: File content as bytes
        filename: The filename (used to determine type)

    Returns:
        Formatted context string, or error message if no provider available.
    """
    _initialize_providers()
    ext = Path(filename).suffix.lower()

    # Map extensions to providers
    ext_to_provider = {
        ".pdf": "pdf",
    }

    provider = ext_to_provider.get(ext)
    if provider and provider in _bytes_processors:
        return _bytes_processors[provider](data, filename)

    return f"\n\nUnsupported file type: {ext}\n"


def is_provider_available(provider: str) -> bool:
    """Check if a provider is available and loaded.

    Args:
        provider: The provider name (e.g., 'pdf')

    Returns:
        True if the provider is available.
    """
    _initialize_providers()
    return provider in _file_processors or provider in _bytes_processors


def list_available_providers() -> list[str]:
    """List all available (loaded) providers.

    Returns:
        List of provider names.
    """
    _initialize_providers()
    return list(set(_file_processors.keys()) | set(_bytes_processors.keys()))
