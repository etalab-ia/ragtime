"""Inspect AI scorers for rag-facile RAG pipeline evaluation.

Answer-quality scorers (LLM-as-judge):

- :func:`faithfulness`        — is the answer grounded in the retrieved context?
- :func:`answer_correctness`  — does the answer match the reference answer?

Retrieval-quality scorers (classical IR, no LLM calls):

- :func:`context_recall`      — fraction of relevant passages covered by retrieval
- :func:`context_precision`   — fraction of retrieved passages that are relevant

Both retrieval scorers use **token-F1 overlap** to match passages, so they work
with any dataset that stores passage text — synthetic or human gold standard —
with no dependency on chunk IDs.
"""

from __future__ import annotations

import re

from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.scorer import (
    Score,
    Scorer,
    Target,
    mean,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState


# ── Judge prompts ─────────────────────────────────────────────────────────────

FAITHFULNESS_TEMPLATE = """\
You are an impartial judge evaluating whether an answer is faithful to the \
provided context. An answer is faithful if every claim it makes is supported \
by the context. Invented or hallucinated information is NOT faithful.

## Context
{context}

## Answer
{answer}

## Instructions
1. List each factual claim in the answer (one per line, prefixed with "- ").
2. For each claim, state whether it is SUPPORTED or NOT SUPPORTED by the context.
3. Finally, output a single line:
   SCORE: <float between 0.0 and 1.0>
   where 1.0 means all claims are supported and 0.0 means none are.

Be strict: if a claim adds information not present in the context, mark it NOT SUPPORTED.
"""

ANSWER_CORRECTNESS_TEMPLATE = """\
You are evaluating whether a model answer correctly addresses a question \
compared to a reference answer.

## Question
{question}

## Reference Answer
{reference}

## Model Answer
{answer}

## Instructions
1. List the key facts in the reference answer (one per line, prefixed with "- ").
2. For each key fact, state whether the model answer COVERS or MISSES it.
3. Finally, output a single line:
   SCORE: <float between 0.0 and 1.0>
   where 1.0 means all key facts are covered and 0.0 means none are.

Be fair: accept paraphrases and equivalent expressions, not just exact matches.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_score(text: str) -> float:
    """Extract the SCORE: <float> from judge output, clamped to [0, 1]."""
    match = re.search(r"SCORE:\s*([\d.]+)", text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        return max(0.0, min(1.0, value))
    return 0.0


# Keep old name as alias for backwards compatibility with tests
_parse_faithfulness_score = _parse_score


def _normalize_tokens(text: str) -> set[str]:
    """Normalize text to a bag of tokens, SQuAD-style.

    Steps (order matters):
    1. Lowercase
    2. Replace punctuation with spaces (so ``"encryption,"`` → ``"encryption"``)
    3. Split on whitespace and discard empty tokens
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return set(text.split())


def _token_f1(a: str, b: str) -> float:
    """Token-level F1 between two texts (bag-of-words), SQuAD-style.

    Normalizes both strings (lowercase + strip punctuation) before computing
    precision/recall/F1 over the token sets.

    Returns:
        Float in [0, 1].  Returns 0.0 if either string is empty.
    """
    tokens_a = _normalize_tokens(a)
    tokens_b = _normalize_tokens(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    precision = intersection / len(tokens_a)
    recall = intersection / len(tokens_b)
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _any_match(text: str, candidates: list[str], threshold: float) -> bool:
    """Return True if *text* has token-F1 ≥ *threshold* with any candidate."""
    return any(_token_f1(text, c) >= threshold for c in candidates)


# ── Primary scorers ───────────────────────────────────────────────────────────


@scorer(metrics=[mean(), stderr()])
def faithfulness(model: str | None = None) -> Scorer:
    """LLM-as-judge: is the model's answer grounded in the retrieved context?

    Reads ``retrieved_contexts`` from ``state.metadata`` (set by the
    ``retrieve_rag_context`` solver).  Returns 1.0 (vacuously true) when no
    context is available — faithfulness is meaningless without context.

    Args:
        model: Grader model identifier (e.g. ``"openai/openweight-medium"``).
            When *None*, uses the task's default model.
    """

    async def score(state: TaskState, target: Target) -> Score:  # noqa: ARG001
        contexts = state.metadata.get("retrieved_contexts", [])
        context = "\n\n---\n\n".join(contexts) if contexts else ""
        answer = state.output.completion if state.output else ""

        if not answer:
            return Score(value=0.0, explanation="No answer generated")
        if not context:
            return Score(
                value=1.0,
                explanation="No context retrieved — faithfulness check skipped",
            )

        prompt = FAITHFULNESS_TEMPLATE.format(context=context, answer=answer)
        grader = get_model(model) if model else get_model()
        result = await grader.generate(prompt, config=GenerateConfig(temperature=0.0))
        judge_output = result.completion

        return Score(value=_parse_score(judge_output), explanation=judge_output)

    return score


@scorer(metrics=[mean(), stderr()])
def answer_correctness(model: str | None = None) -> Scorer:
    """LLM-as-judge: does the model's answer match the reference answer?

    Compares the generated answer against the ground-truth reference stored
    in the Inspect AI ``Target``.  Returns 1.0 (vacuously true) when no
    reference is available.

    Args:
        model: Grader model identifier (e.g. ``"openai/openweight-medium"``).
            When *None*, uses the task's default model.
    """

    async def score(state: TaskState, target: Target) -> Score:
        question = state.input_text
        reference = target.target if hasattr(target, "target") else str(target)
        answer = state.output.completion if state.output else ""

        if not answer:
            return Score(value=0.0, explanation="No answer generated")
        if not reference:
            return Score(
                value=1.0, explanation="No reference answer — correctness check skipped"
            )

        prompt = ANSWER_CORRECTNESS_TEMPLATE.format(
            question=question,
            reference=reference,
            answer=answer,
        )
        grader = get_model(model) if model else get_model()
        result = await grader.generate(prompt, config=GenerateConfig(temperature=0.0))
        judge_output = result.completion

        return Score(value=_parse_score(judge_output), explanation=judge_output)

    return score


# ── Retrieval-quality scorers (classical IR, no LLM calls) ────────────────────


@scorer(metrics=[mean(), stderr()])
def context_recall(threshold: float = 0.5) -> Scorer:
    """Fraction of relevant passages covered by the retrieved context.

    For each passage in ``relevant_contexts`` (captured during dataset
    generation), checks whether any retrieved chunk has a token-F1 score
    ≥ *threshold* against it.

    Works with any dataset that stores passage text — synthetic or gold
    standard.  No chunk IDs required, no LLM calls.

    Args:
        threshold: Minimum token-F1 to count a retrieved chunk as covering a
            relevant passage.  Defaults to 0.5 (SQuAD loose-match convention).
    """

    async def score(state: TaskState, target: Target) -> Score:  # noqa: ARG001
        relevant: list[str] = state.metadata.get("relevant_contexts", [])
        retrieved: list[str] = state.metadata.get("retrieved_contexts", [])

        if not relevant:
            return Score(
                value=1.0,
                explanation="No relevant contexts defined — vacuously true",
            )
        if not retrieved:
            return Score(value=0.0, explanation="No context retrieved")

        covered = sum(1 for rel in relevant if _any_match(rel, retrieved, threshold))
        recall = covered / len(relevant)
        return Score(
            value=recall,
            explanation=(
                f"{covered}/{len(relevant)} relevant passages covered "
                f"(token-F1 ≥ {threshold})"
            ),
        )

    return score


@scorer(metrics=[mean(), stderr()])
def context_precision(threshold: float = 0.5) -> Scorer:
    """Fraction of retrieved passages that overlap with a relevant passage.

    For each passage in ``retrieved_contexts``, checks whether it has a
    token-F1 score ≥ *threshold* against any passage in ``relevant_contexts``.

    Works with any dataset that stores passage text — synthetic or gold
    standard.  No chunk IDs required, no LLM calls.

    Args:
        threshold: Minimum token-F1 to count a retrieved chunk as relevant.
            Defaults to 0.5 (SQuAD loose-match convention).
    """

    async def score(state: TaskState, target: Target) -> Score:  # noqa: ARG001
        relevant: list[str] = state.metadata.get("relevant_contexts", [])
        retrieved: list[str] = state.metadata.get("retrieved_contexts", [])

        if not retrieved:
            return Score(
                value=1.0,
                explanation="No context retrieved — vacuously true",
            )
        if not relevant:
            return Score(
                value=1.0,
                explanation="No relevant contexts defined — vacuously true",
            )

        hits = sum(1 for ret in retrieved if _any_match(ret, relevant, threshold))
        precision = hits / len(retrieved)
        return Score(
            value=precision,
            explanation=(
                f"{hits}/{len(retrieved)} retrieved passages are relevant "
                f"(token-F1 ≥ {threshold})"
            ),
        )

    return score


# ── Convenience ───────────────────────────────────────────────────────────────


def rag_eval_scorer(model: str | None = None) -> list[Scorer]:
    """Return the full list of RAG evaluation scorers.

    Includes retrieval-quality scorers (no LLM) and answer-quality scorers
    (LLM-as-judge).  Pass as ``scorer=rag_eval_scorer(model)`` in a Task.
    """
    return [
        context_recall(),
        context_precision(),
        faithfulness(model=model),
        answer_correctness(model=model),
    ]
