"""RAG evaluation with Inspect AI.

Provides scorers, dataset adapters, solvers, and tasks for evaluating
rag-facile RAG pipelines using the Inspect AI framework.
"""

from rag_facile.evaluation._dataset import load_rag_dataset
from rag_facile.evaluation._scorers import (
    answer_correctness,
    context_precision,
    context_recall,
    faithfulness,
    rag_eval_scorer,
)
from rag_facile.evaluation._solvers import retrieve_rag_context
from rag_facile.evaluation._tasks import rag_eval


__all__ = [
    "answer_correctness",
    "context_precision",
    "context_recall",
    "faithfulness",
    "load_rag_dataset",
    "rag_eval",
    "rag_eval_scorer",
    "retrieve_rag_context",
]
