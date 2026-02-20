"""RAG Facile chat agent tools.

Each @tool is callable by the smolagents ToolCallingAgent during a chat session.
The workspace root is set once at session start by the agent harness.
"""

from pathlib import Path

from smolagents import tool


# Module-level workspace reference — set by the agent harness at session start.
_workspace_root: Path | None = None


def set_workspace_root(root: Path) -> None:
    """Register the workspace root so tools can locate project files."""
    global _workspace_root
    _workspace_root = root


@tool
def get_ragfacile_config() -> str:
    """Read the current ragfacile.toml configuration.

    Use this to answer questions about the RAG pipeline settings such as
    which preset is active, retrieval parameters, collection IDs, etc.
    """
    if _workspace_root is None:
        return (
            "No workspace detected — ragfacile.toml was not found in the current "
            "directory or any parent directory. "
            "Run 'rag-facile setup' to create a workspace."
        )
    config_file = _workspace_root / "ragfacile.toml"
    if not config_file.exists():
        return (
            "No ragfacile.toml found in this workspace. "
            "Run 'rag-facile setup' to create one."
        )
    return config_file.read_text(encoding="utf-8")
