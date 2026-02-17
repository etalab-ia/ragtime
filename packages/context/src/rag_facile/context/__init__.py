"""Context - format retrieved chunks into LLM-ready context strings.

This package provides context assembly capabilities for the RAG pipeline.
It converts retrieved document chunks into formatted context strings
suitable for injection into LLM prompts, with optional citations.

Example usage::

    from rag_facile.context import format_context

    context_str = format_context(chunks, include_citations=True)

.. note::
    For vector search, use the ``retrieval`` package.
    For reranking, use the ``reranking`` package.
"""

from rag_facile.context.formatter import format_context

__all__ = [
    "format_context",
]
