"""Tests for RAG evaluation scorers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_facile.evaluation._scorers import (
    _normalize_tokens,
    _parse_faithfulness_score,
    _parse_score,
    _token_f1,
    answer_correctness,
    context_precision,
    context_recall,
    faithfulness,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_state(
    *,
    relevant_contexts: list[str] | None = None,
    retrieved_contexts: list[str] | None = None,
    completion: str = "test answer",
    input_text: str = "test question",
) -> MagicMock:
    """Create a mock TaskState with metadata."""
    state = MagicMock()
    state.metadata = {
        "relevant_contexts": relevant_contexts or [],
        "retrieved_contexts": retrieved_contexts or [],
    }
    state.output = MagicMock()
    state.output.completion = completion
    state.input_text = input_text
    return state


def _make_target(text: str = "reference answer") -> MagicMock:
    target = MagicMock()
    target.target = text
    return target


# ── score parser ──────────────────────────────────────────────────────────────


def test_parse_score_valid() -> None:
    assert _parse_score("SCORE: 0.85") == 0.85


def test_parse_score_lowercase() -> None:
    assert _parse_score("score: 0.5") == 0.5


def test_parse_score_clamped() -> None:
    assert _parse_score("SCORE: 1.5") == 1.0
    assert _parse_score("SCORE: -0.3") == 0.0


def test_parse_score_missing() -> None:
    assert _parse_score("no score here") == 0.0


def test_parse_faithfulness_score_alias() -> None:
    """Backwards-compat alias still works."""
    assert _parse_faithfulness_score("SCORE: 0.75") == 0.75


# ── _token_f1 ─────────────────────────────────────────────────────────────────


def test_normalize_tokens_strips_punctuation() -> None:
    assert _normalize_tokens("encryption,") == {"encryption"}
    assert _normalize_tokens("données.") == {"données"}
    assert _normalize_tokens("(article 5)") == {"article", "5"}


def test_token_f1_identical() -> None:
    assert _token_f1("le chat est sur le toit", "le chat est sur le toit") == 1.0


def test_token_f1_no_overlap() -> None:
    assert _token_f1("chien maison voiture", "soleil lune étoile") == 0.0


def test_token_f1_partial() -> None:
    score = _token_f1("le chat noir", "le chat blanc")
    # "le" and "chat" overlap → 2/3 precision, 2/3 recall, F1 = 2/3
    assert 0.6 < score < 0.7


def test_token_f1_empty() -> None:
    assert _token_f1("", "some text") == 0.0
    assert _token_f1("some text", "") == 0.0


def test_token_f1_subset() -> None:
    # 2 tokens match out of 2 vs 7: recall=1.0, precision=2/7, F1≈0.44
    score = _token_f1(
        "homomorphic encryption",
        "homomorphic encryption allows computation on encrypted data",
    )
    assert 0.4 < score < 0.5


def test_token_f1_punctuation_normalized() -> None:
    """Punctuation must not prevent matches — 'encryption,' == 'encryption'."""
    assert _token_f1("encryption, data", "encryption data") == 1.0


def test_token_f1_case_insensitive() -> None:
    assert _token_f1("Données Personnelles", "données personnelles") == 1.0


def test_token_f1_mixed_punctuation() -> None:
    """Real French government prose: commas, periods, parentheses stripped."""
    a = "L'article 5 (alinéa 2) dispose que les données doivent être protégées."
    b = "L article 5 alinéa 2 dispose que les données doivent être protégées"
    assert _token_f1(a, b) > 0.9


# ── context_recall ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_context_recall_perfect() -> None:
    """All relevant passages are covered."""
    scorer = context_recall()
    state = _make_state(
        relevant_contexts=["homomorphic encryption allows computation"],
        retrieved_contexts=[
            "homomorphic encryption allows computation on encrypted data"
        ],
    )
    result = await scorer(state, _make_target())
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_context_recall_partial() -> None:
    """Only some relevant passages are covered."""
    scorer = context_recall()
    state = _make_state(
        relevant_contexts=[
            "homomorphic encryption allows computation",  # covered
            "quantum computing uses qubits",  # not covered
        ],
        retrieved_contexts=[
            "homomorphic encryption allows computation on encrypted data"
        ],
    )
    result = await scorer(state, _make_target())
    assert result.value == 0.5


@pytest.mark.asyncio
async def test_context_recall_no_relevant() -> None:
    """No relevant contexts defined → vacuously true."""
    scorer = context_recall()
    state = _make_state(relevant_contexts=[], retrieved_contexts=["some text"])
    result = await scorer(state, _make_target())
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_context_recall_nothing_retrieved() -> None:
    """Nothing retrieved → recall is 0."""
    scorer = context_recall()
    state = _make_state(
        relevant_contexts=["some relevant text"],
        retrieved_contexts=[],
    )
    result = await scorer(state, _make_target())
    assert result.value == 0.0


# ── context_precision ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_context_precision_perfect() -> None:
    """All retrieved passages are relevant."""
    scorer = context_precision()
    state = _make_state(
        relevant_contexts=["homomorphic encryption allows computation"],
        retrieved_contexts=[
            "homomorphic encryption allows computation on encrypted data"
        ],
    )
    result = await scorer(state, _make_target())
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_context_precision_partial() -> None:
    """Only some retrieved passages are relevant."""
    scorer = context_precision()
    state = _make_state(
        relevant_contexts=["homomorphic encryption allows computation"],
        retrieved_contexts=[
            "homomorphic encryption allows computation on encrypted data",  # relevant
            "the weather in Paris is often rainy in winter",  # not relevant
        ],
    )
    result = await scorer(state, _make_target())
    assert result.value == 0.5


@pytest.mark.asyncio
async def test_context_precision_no_retrieved() -> None:
    """Nothing retrieved → vacuously true."""
    scorer = context_precision()
    state = _make_state(relevant_contexts=["some text"], retrieved_contexts=[])
    result = await scorer(state, _make_target())
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_context_precision_no_relevant() -> None:
    """No relevant contexts defined → vacuously true."""
    scorer = context_precision()
    state = _make_state(relevant_contexts=[], retrieved_contexts=["some text"])
    result = await scorer(state, _make_target())
    assert result.value == 1.0


# ── faithfulness ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_faithfulness_no_answer() -> None:
    scorer = faithfulness(model="test")
    state = _make_state(retrieved_contexts=["some context"], completion="")
    result = await scorer(state, _make_target())
    assert result.value == 0.0


@pytest.mark.asyncio
async def test_faithfulness_no_context() -> None:
    """No context → vacuously true (we can't judge faithfulness without context)."""
    scorer = faithfulness(model="test")
    state = _make_state(retrieved_contexts=[], completion="some answer")
    result = await scorer(state, _make_target())
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_faithfulness_calls_grader() -> None:
    """Faithfulness scorer calls the grader model and parses SCORE."""
    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.completion = "- Claim A: SUPPORTED\nSCORE: 0.9"
    mock_model.generate = AsyncMock(return_value=mock_result)

    with patch("rag_facile.evaluation._scorers.get_model", return_value=mock_model):
        scorer = faithfulness(model="test")
        state = _make_state(
            retrieved_contexts=["Paris is the capital of France."],
            completion="France's capital is Paris.",
        )
        result = await scorer(state, _make_target())

    assert result.value == 0.9


# ── answer_correctness ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_correctness_no_answer() -> None:
    scorer = answer_correctness(model="test")
    state = _make_state(completion="")
    result = await scorer(state, _make_target("reference"))
    assert result.value == 0.0


@pytest.mark.asyncio
async def test_answer_correctness_no_reference() -> None:
    """No reference → vacuously true."""
    scorer = answer_correctness(model="test")
    state = _make_state(completion="some answer")
    result = await scorer(state, _make_target(""))
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_answer_correctness_calls_grader() -> None:
    """answer_correctness calls the grader model and parses SCORE."""
    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.completion = "- Fact 1: COVERS\n- Fact 2: COVERS\nSCORE: 1.0"
    mock_model.generate = AsyncMock(return_value=mock_result)

    with patch("rag_facile.evaluation._scorers.get_model", return_value=mock_model):
        scorer = answer_correctness(model="test")
        state = _make_state(completion="The capital of France is Paris.")
        result = await scorer(state, _make_target("Paris is the capital of France."))

    assert result.value == 1.0
