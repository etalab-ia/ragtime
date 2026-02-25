"""Tests for RAG evaluation solvers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_facile.evaluation._solvers import retrieve_rag_context


# ── Helpers ───────────────────────────────────────────────────────────────────

# Patch target: the module-level helper that calls the RAG pipeline.
# Tests patch this instead of the lazily-imported rag_facile.core / .pipelines
# modules (which aren't available in the evaluation package's test environment).
_PIPELINE_HELPER = "rag_facile.evaluation._solvers._call_pipeline"


def _make_state(question: str = "What is RAG?") -> MagicMock:
    """Create a mock TaskState."""
    from inspect_ai.model import ChatMessageUser

    state = MagicMock()
    state.input_text = question
    state.metadata = {}
    state.messages = [ChatMessageUser(content=question)]
    return state


# ── retrieve_rag_context ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieve_injects_context() -> None:
    """Pipeline returns (formatted_context, chunk_texts) — both stored correctly."""
    chunk_texts = [
        "RAG stands for Retrieval-Augmented Generation.",
        "It combines retrieval with generation.",
    ]
    with patch(
        _PIPELINE_HELPER,
        return_value=("RAG stands for Retrieval-Augmented Generation.", chunk_texts),
    ):
        solver = retrieve_rag_context()
        state = _make_state("What is RAG?")
        result = await solver(state, AsyncMock())

    # Individual chunk texts stored for context_recall / context_precision
    assert result.metadata["retrieved_contexts"] == chunk_texts

    # Formatted context injected into the first message
    first_message = result.messages[0]
    assert "Retrieval-Augmented Generation" in first_message.content
    assert "What is RAG?" in first_message.content


@pytest.mark.asyncio
async def test_retrieve_no_context_keeps_dataset_values() -> None:
    """When pipeline returns no context, dataset's pre-computed values are kept."""
    with patch(_PIPELINE_HELPER, return_value=("", [])):
        solver = retrieve_rag_context()
        state = _make_state("What is RAG?")
        # Pre-populate with dataset's pre-computed values (loaded by _dataset.py)
        state.metadata = {
            "relevant_contexts": ["The relevant passage about RAG."],
            "retrieved_contexts": ["Context from dataset generation"],
        }
        result = await solver(state, AsyncMock())

    # Dataset values untouched — used by scorers for static evaluation
    assert result.metadata["relevant_contexts"] == ["The relevant passage about RAG."]
    assert result.metadata["retrieved_contexts"] == ["Context from dataset generation"]


@pytest.mark.asyncio
async def test_retrieve_pipeline_failure_passthrough() -> None:
    """When the pipeline raises, state is passed through unchanged (non-fatal)."""
    with patch(_PIPELINE_HELPER, side_effect=RuntimeError("pipeline unavailable")):
        solver = retrieve_rag_context()
        state = _make_state("What is RAG?")
        result = await solver(state, AsyncMock())

    assert result is state
    assert "retrieved_contexts" not in result.metadata
