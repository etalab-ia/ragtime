"""Inspect AI task definitions for rag-facile evaluation."""

from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.solver import generate

from rag_facile.evaluation._dataset import load_rag_dataset
from rag_facile.evaluation._scorers import (
    answer_correctness,
    context_precision,
    context_recall,
    faithfulness,
)
from rag_facile.evaluation._solvers import retrieve_rag_context


@task
def rag_eval(
    dataset_path: str = "data/datasets/golden_v1.jsonl",
    grader_model: str = "openai/openweight-medium",
) -> Task:
    """End-to-end evaluation of a rag-facile RAG pipeline.

    For each sample in the dataset:

    1. **Retrieve** — ``retrieve_rag_context`` calls ``AlbertPipeline.process_query``
       and stores individual chunk texts in ``state.metadata["retrieved_contexts"]``.
    2. **Generate** — the model answers the question given the retrieved context.
    3. **Score** — four metrics:

       Retrieval quality (classical IR, no LLM calls):

       - *context_recall*: fraction of relevant passages covered by retrieval
         (token-F1 ≥ 0.5 against ``relevant_contexts`` from the dataset)
       - *context_precision*: fraction of retrieved passages that are relevant
         (token-F1 ≥ 0.5 against ``relevant_contexts`` from the dataset)

       Answer quality (LLM-as-judge):

       - *faithfulness*: is the answer grounded in the retrieved context?
       - *answer_correctness*: does the answer match the reference answer?

    The dataset needs ``user_input``, ``reference``, and ``relevant_contexts``
    fields.  Works with synthetic datasets (from ``rag-facile generate-dataset``)
    and human gold-standard datasets alike — no chunk IDs required.

    Args:
        dataset_path: Path to a rag-facile JSONL dataset.
        grader_model: Model identifier for the LLM-as-judge scorers.
    """
    return Task(
        dataset=load_rag_dataset(dataset_path),
        solver=[retrieve_rag_context(), generate()],
        scorer=[
            context_recall(),
            context_precision(),
            faithfulness(model=grader_model),
            answer_correctness(model=grader_model),
        ],
    )
