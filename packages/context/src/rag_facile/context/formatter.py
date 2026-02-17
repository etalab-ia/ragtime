"""Format retrieved chunks as LLM context.

Provides functions to format search results into context strings
suitable for injection into LLM prompts, with optional citations.
"""

from __future__ import annotations

import logging

from rag_facile.core import RetrievedChunk, get_config


logger = logging.getLogger(__name__)


def format_context(
    chunks: list[RetrievedChunk],
    *,
    include_citations: bool | None = None,
    citation_style: str | None = None,
) -> str:
    """Format chunks as a context string for LLM injection.

    Args:
        chunks: Retrieved chunks to format.
        include_citations: Include source citations (defaults to config).
        citation_style: "inline" or "footnote" (defaults to config).

    Returns:
        Formatted context string. Empty string if no chunks.

    Example output (inline citations):
        --- Retrieved context ---
        [1] La loi Energie Climat vise a... (source: rapport.pdf, p.5)
        [2] Les energies renouvelables... (source: guide.pdf, p.12)
        --- End of context ---
    """
    if not chunks:
        return ""

    config = get_config()
    include_citations = (
        include_citations
        if include_citations is not None
        else config.formatting.citations.enabled
    )
    citation_style = (
        citation_style
        if citation_style is not None
        else config.formatting.citations.style
    )

    lines: list[str] = ["", "--- Retrieved context ---"]

    for i, chunk in enumerate(chunks, 1):
        content = chunk["content"].strip()

        if include_citations:
            # Build source reference
            source_parts: list[str] = []
            if chunk["source_file"]:
                source_parts.append(f"source: {chunk['source_file']}")
            if chunk["page"] is not None:
                source_parts.append(f"p.{chunk['page']}")
            source_ref = f" ({', '.join(source_parts)})" if source_parts else ""

            if citation_style == "footnote":
                lines.append(f"{content} [{i}]")
            else:
                # Default: inline
                lines.append(f"[{i}] {content}{source_ref}")
        else:
            lines.append(content)

        # Add separator between chunks
        if i < len(chunks):
            lines.append("")

    lines.append("--- End of context ---")
    lines.append("")

    return "\n".join(lines)
