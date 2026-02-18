"""Unit tests for query expansion strategies.

All LLM calls are mocked so tests run without a live Albert API key.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import openai
import pytest

from rag_facile.query._models import ExpandedQueries, HypotheticalDocument
from rag_facile.query.hyde import HyDEExpander
from rag_facile.query.multi_query import MultiQueryExpander


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    strategy: str = "multi_query",
    num_variations: int = 3,
    include_original: bool = True,
    model: str = "openweight-medium",
):
    """Build a minimal config stub."""
    cfg = MagicMock()
    cfg.query.strategy = strategy
    cfg.query.num_variations = num_variations
    cfg.query.include_original = include_original
    cfg.query.model = model
    return cfg


def _make_client(instructor_return_value):
    """Build an AlbertClient stub whose as_instructor() returns a mock."""
    instructor_mock = MagicMock()
    instructor_mock.chat.completions.create.return_value = instructor_return_value
    client = MagicMock()
    client.as_instructor.return_value = instructor_mock
    return client


# ---------------------------------------------------------------------------
# MultiQueryExpander tests
# ---------------------------------------------------------------------------


class TestMultiQueryExpander:
    def test_expand_prepends_original_by_default(self):
        expected = ExpandedQueries(
            variations=[
                "Aide Personnalisée au Logement conditions d'attribution",
                "demande APL logement social CAF",
                "bénéficier aide au logement code construction",
            ],
            reasoning="APL expanded to full administrative name",
        )
        client = _make_client(expected)
        expander = MultiQueryExpander(client, _make_config())

        result = expander.expand("comment toucher les APL ?")

        assert result[0] == "comment toucher les APL ?"
        assert len(result) == 4  # original + 3 variations
        assert result[1:] == expected.variations

    def test_expand_without_original(self):
        expected = ExpandedQueries(
            variations=[
                "Carte Nationale d'Identité démarche",
                "renouvellement CNI préfecture",
            ],
            reasoning="CNI expanded",
        )
        client = _make_client(expected)
        expander = MultiQueryExpander(client, _make_config(include_original=False))

        result = expander.expand("renouveler ma CNI")

        assert "renouveler ma CNI" not in result
        assert result == expected.variations

    def test_expand_falls_back_on_llm_error(self):
        client = MagicMock()
        instructor_mock = MagicMock()
        instructor_mock.chat.completions.create.side_effect = openai.APIConnectionError(
            request=MagicMock()
        )
        client.as_instructor.return_value = instructor_mock

        expander = MultiQueryExpander(client, _make_config())
        result = expander.expand("ma question")

        assert result == ["ma question"]

    def test_expand_calls_instructor_with_correct_model(self):
        expected = ExpandedQueries(variations=["v1"], reasoning="r")
        client = _make_client(expected)
        expander = MultiQueryExpander(client, _make_config(model="openweight-small"))

        expander.expand("query")

        call_kwargs = client.as_instructor().chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "openweight-small"
        assert call_kwargs.kwargs["response_model"] is ExpandedQueries

    def test_expand_num_variations_in_prompt(self):
        expected = ExpandedQueries(variations=["v1", "v2"], reasoning="r")
        client = _make_client(expected)
        expander = MultiQueryExpander(client, _make_config(num_variations=2))

        expander.expand("query")

        prompt = client.as_instructor().chat.completions.create.call_args.kwargs[
            "messages"
        ][1]["content"]
        assert "2" in prompt


# ---------------------------------------------------------------------------
# HyDEExpander tests
# ---------------------------------------------------------------------------


class TestHyDEExpander:
    def test_expand_returns_hypothetical_content(self):
        doc = HypotheticalDocument(
            content="Conformément à l'article L. 821-1 du code de la sécurité sociale...",
            document_type="notice informative",
            keywords=["APL", "aide au logement"],
        )
        client = _make_client(doc)
        expander = HyDEExpander(client, _make_config(strategy="hyde"))

        result = expander.expand("comment toucher les APL ?")

        assert result[0] == "comment toucher les APL ?"  # include_original=True
        assert result[1] == doc.content
        assert len(result) == 2

    def test_expand_hyde_without_original(self):
        doc = HypotheticalDocument(
            content="Le licenciement est régi par...",
            document_type="circulaire",
        )
        client = _make_client(doc)
        expander = HyDEExpander(
            client, _make_config(strategy="hyde", include_original=False)
        )

        result = expander.expand("je me suis fait virer")

        assert result == [doc.content]

    def test_expand_falls_back_on_llm_error(self):
        client = MagicMock()
        instructor_mock = MagicMock()
        instructor_mock.chat.completions.create.side_effect = openai.APIConnectionError(
            request=MagicMock()
        )
        client.as_instructor.return_value = instructor_mock

        expander = HyDEExpander(client, _make_config(strategy="hyde"))
        result = expander.expand("ma question")

        assert result == ["ma question"]

    def test_expand_calls_instructor_with_hypothetical_document_model(self):
        doc = HypotheticalDocument(content="...", document_type="décret")
        client = _make_client(doc)
        expander = HyDEExpander(client, _make_config(strategy="hyde"))

        expander.expand("query")

        call_kwargs = client.as_instructor().chat.completions.create.call_args
        assert call_kwargs.kwargs["response_model"] is HypotheticalDocument


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestGetExpander:
    def test_get_expander_multi_query(self):
        from rag_facile.query import get_expander
        from rag_facile.query.multi_query import MultiQueryExpander

        client = MagicMock()
        config = _make_config(strategy="multi_query")
        expander = get_expander(client, config)
        assert isinstance(expander, MultiQueryExpander)

    def test_get_expander_hyde(self):
        from rag_facile.query import get_expander
        from rag_facile.query.hyde import HyDEExpander

        client = MagicMock()
        config = _make_config(strategy="hyde")
        expander = get_expander(client, config)
        assert isinstance(expander, HyDEExpander)

    def test_get_expander_unknown_raises(self):
        from rag_facile.query import get_expander

        client = MagicMock()
        config = _make_config(strategy="unknown_strategy")
        with pytest.raises(ValueError, match="Unknown query expansion strategy"):
            get_expander(client, config)
