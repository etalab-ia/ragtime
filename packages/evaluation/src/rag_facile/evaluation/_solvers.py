"""Custom Inspect AI solvers for rag-facile evaluation."""

from __future__ import annotations

import asyncio
import logging

from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, TaskState, solver


logger = logging.getLogger(__name__)


def _call_pipeline(question: str) -> tuple[str, list[str]]:
    """Call the RAG pipeline and return formatted context + individual chunk texts.

    Returns:
        tuple of (formatted_context, list_of_chunk_texts)

        - formatted_context: joined, citation-annotated string for injection into
          the LLM prompt (produced by ``process_query``).
        - list_of_chunk_texts: individual passage texts after search + rerank,
          stored in ``state.metadata["retrieved_contexts"]`` for the
          ``context_recall`` and ``context_precision`` scorers.

    Extracted as a module-level helper so tests can patch it cleanly.
    """
    from rag_facile.core import get_config
    from rag_facile.pipelines import get_pipeline
    from rag_facile.retrieval import search_chunks

    config = get_config()
    pipeline = get_pipeline(config)

    # Formatted context for the LLM prompt
    context = pipeline.process_query(question)

    # Re-run search + rerank to capture individual chunk texts.
    # process_query doesn't expose them, so we replicate the same call.
    try:
        from rag_facile.reranking import rerank_chunks

        collection_ids = list(config.storage.collections)
        if pipeline._collection_id:
            collection_ids = list(set(collection_ids) | {pipeline._collection_id})

        if collection_ids:
            client = pipeline.client
            chunks = search_chunks(
                client,
                question,
                collection_ids,
                limit=config.retrieval.top_k,
                method=config.retrieval.strategy,
                score_threshold=config.retrieval.score_threshold,
            )

            final_chunks = chunks
            if config.reranking.enabled:
                final_chunks = rerank_chunks(
                    client,
                    question,
                    chunks,
                    model=config.reranking.model,
                    top_n=config.reranking.top_n,
                )

            chunk_texts = [
                chunk.get("content", "")
                for chunk in final_chunks
                if chunk.get("content")
            ]
            return context, chunk_texts

    except Exception:
        logger.warning("Failed to extract chunk texts from search", exc_info=True)

    return context, []


@solver
def retrieve_rag_context() -> Solver:
    """Run the RAG pipeline and inject retrieved context into the prompt.

    Calls ``AlbertPipeline.process_query()`` using the collections configured
    in ``ragfacile.toml``.  The retrieved context is injected as a prefix to
    the user message.

    Two metadata keys are written for the scorers:

    - ``retrieved_contexts``: list[str] — individual chunk texts after
      search + rerank.  Used by ``context_recall`` and ``context_precision``
      (token-F1 comparison against ``relevant_contexts`` from the dataset).
    - The dataset's ``relevant_contexts`` are left untouched so scorers can
      compare retrieved vs relevant.

    If the pipeline returns no context (no collections configured, or no
    relevant chunks found), the dataset's pre-computed values are kept and the
    prompt is passed through unchanged.
    """

    async def solve(state: TaskState, generate: object) -> TaskState:  # noqa: ARG001
        question = state.input_text

        try:
            # process_query is synchronous — run in a thread to avoid blocking
            # the Inspect AI event loop.
            loop = asyncio.get_event_loop()
            context, chunk_texts = await loop.run_in_executor(
                None, _call_pipeline, question
            )
        except Exception:
            logger.warning("RAG pipeline retrieval failed", exc_info=True)
            context = ""
            chunk_texts = []

        if context:
            # Overwrite with live retrieval results.
            # chunk_texts are individual passage texts for recall/precision scoring.
            state.metadata["retrieved_contexts"] = chunk_texts

        augmented = (
            "Use the following context to answer the question. "
            "Only use information from the context. "
            "If the context does not contain the answer, say so.\n\n"
            f"## Context\n{context}\n\n"
            f"## Question\n{question}"
        )
        state.messages = [
            ChatMessageUser(content=augmented),
            *state.messages[1:],
        ]
        return state

    return solve
