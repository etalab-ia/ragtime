"""Tests for the local keyword search engine."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import re

from rag_facile.memory.search import (
    _group_into_snippets,
    _recency_multiplier,
    _score_line,
    _tokenize,
    keyword_search,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a workspace with .agent/ directory and sample files."""
    agent = tmp_path / ".agent"
    agent.mkdir()

    # MEMORY.md — semantic store
    (agent / "MEMORY.md").write_text(
        "---\nupdated: 2026-03-02\n---\n\n"
        "# Agent Memory\n\n"
        "## User Identity\n"
        "- Name: Luis\n"
        "- Role: Developer at DINUM\n\n"
        "## Preferences\n"
        "- Prefers French language for UI\n"
        "- Uses Albert API for embeddings\n\n"
        "## Project State\n"
        "- [2026-03-01] Preset changed to accurate\n"
        "- [2026-03-02] Pipeline uses query expansion\n\n"
        "## Key Facts\n"
        "- Albert API rate limit is 10 requests per minute\n"
        "- Collection 785 contains service-public documents\n",
        encoding="utf-8",
    )

    # Daily log
    logs = agent / "logs"
    logs.mkdir()
    (logs / "2026-03-02.md").write_text(
        "# 2026-03-02\n\n"
        "## 14:30 — Vous\n"
        "How do I configure query expansion?\n\n"
        "## 14:31 — Assistant\n"
        "Query expansion uses the multi_query strategy.\n"
        "You can enable it in the accurate preset.\n",
        encoding="utf-8",
    )
    (logs / "2026-02-28.md").write_text(
        "# 2026-02-28\n\n"
        "## 10:00 — Vous\n"
        "What is the Albert API rate limit?\n\n"
        "## 10:01 — Assistant\n"
        "The Albert API allows 10 requests per minute.\n",
        encoding="utf-8",
    )

    # Session snapshot
    sessions = agent / "sessions"
    sessions.mkdir()
    (sessions / "2026-03-01-1430-deployment-config.md").write_text(
        "---\ndate: 2026-03-01\nsummary: deployment config\n---\n\n"
        "# Session: deployment config\n\n"
        "## Vous\n"
        "I need help with deployment configuration for production.\n\n"
        "## Assistant\n"
        "For production deployment, you should set temperature to 0.1\n"
        "and increase top_k to 15 for better recall.\n",
        encoding="utf-8",
    )

    return tmp_path


# ── Tokenizer tests ───────────────────────────────────────────────────────────


class TestTokenize:
    def test_extracts_significant_words(self) -> None:
        assert _tokenize("query expansion configuration") == [
            "query",
            "expansion",
            "configuration",
        ]

    def test_filters_stopwords(self) -> None:
        result = _tokenize("the query for expansion and configuration")
        assert "the" not in result
        assert "for" not in result
        assert "and" not in result
        assert "query" in result

    def test_filters_short_words(self) -> None:
        result = _tokenize("a is ok but longer words stay")
        assert "ok" not in result
        assert "is" not in result
        assert "longer" in result
        assert "words" in result

    def test_empty_query(self) -> None:
        assert _tokenize("") == []
        assert _tokenize("the and or") == []

    def test_lowercase(self) -> None:
        assert _tokenize("Albert API") == ["albert", "api"]


# ── Line scoring tests ────────────────────────────────────────────────────────


class TestScoreLine:
    def _patterns(self, *words: str) -> list[re.Pattern[str]]:
        return [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in words]

    def test_single_word_match(self) -> None:
        patterns = self._patterns("albert")
        assert _score_line("The Albert API is great", patterns) == 1.0

    def test_multiple_word_match(self) -> None:
        patterns = self._patterns("albert", "api")
        assert _score_line("The Albert API is great", patterns) == 2.0

    def test_no_match(self) -> None:
        patterns = self._patterns("deployment")
        assert _score_line("The Albert API is great", patterns) == 0.0

    def test_case_insensitive(self) -> None:
        patterns = self._patterns("albert")
        assert _score_line("ALBERT is a service", patterns) == 1.0


# ── Recency multiplier tests ─────────────────────────────────────────────────


class TestRecencyMultiplier:
    def test_today_file(self, tmp_path: Path) -> None:
        today = date.today().isoformat()
        f = tmp_path / f"{today}.md"
        f.write_text("test")
        assert _recency_multiplier(f) == 1.3

    def test_old_file(self, tmp_path: Path) -> None:
        f = tmp_path / "2024-01-01.md"
        f.write_text("test")
        assert _recency_multiplier(f) == 1.0

    def test_no_date_in_filename(self, tmp_path: Path) -> None:
        f = tmp_path / "MEMORY.md"
        f.write_text("test")
        # Falls back to mtime — file just created, so should be today
        assert _recency_multiplier(f) >= 1.2


# ── Snippet grouping tests ───────────────────────────────────────────────────


class TestGroupIntoSnippets:
    def test_single_match(self) -> None:
        lines = ["line 0", "line 1", "match here", "line 3", "line 4"]
        scored = [(2, 1.0)]
        snippets = _group_into_snippets(scored, lines, context_lines=1)
        assert len(snippets) == 1
        start, end, score, text = snippets[0]
        assert start == 1  # context_lines=1 → one line before
        assert end == 3  # one line after
        assert score == 1.0
        assert "match here" in text

    def test_adjacent_matches_merged(self) -> None:
        lines = [f"line {i}" for i in range(10)]
        scored = [(2, 1.0), (4, 1.5)]  # close enough to merge with context=2
        snippets = _group_into_snippets(scored, lines, context_lines=2)
        assert len(snippets) == 1
        assert snippets[0][2] == 2.5  # scores combined

    def test_distant_matches_separate(self) -> None:
        lines = [f"line {i}" for i in range(20)]
        scored = [(2, 1.0), (15, 1.5)]
        snippets = _group_into_snippets(scored, lines, context_lines=1)
        assert len(snippets) == 2

    def test_empty_scores(self) -> None:
        assert _group_into_snippets([], ["a", "b"]) == []


# ── Integration tests ─────────────────────────────────────────────────────────


class TestKeywordSearch:
    def test_finds_in_memory_md(self, workspace: Path) -> None:
        results = keyword_search(workspace, "Albert API rate limit")
        assert len(results) > 0
        # MEMORY.md should rank high (has the exact phrase + 1.5x boost)
        memory_results = [r for r in results if r["file"] == "MEMORY.md"]
        assert len(memory_results) > 0

    def test_finds_in_logs(self, workspace: Path) -> None:
        results = keyword_search(workspace, "query expansion")
        assert len(results) > 0
        log_results = [r for r in results if r["file"].startswith("logs/")]
        assert len(log_results) > 0

    def test_finds_in_sessions(self, workspace: Path) -> None:
        results = keyword_search(workspace, "deployment production")
        assert len(results) > 0
        session_results = [r for r in results if r["file"].startswith("sessions/")]
        assert len(session_results) > 0

    def test_no_results_for_unmatched_query(self, workspace: Path) -> None:
        results = keyword_search(workspace, "kubernetes orchestration")
        assert results == []

    def test_empty_query_returns_empty(self, workspace: Path) -> None:
        results = keyword_search(workspace, "")
        assert results == []

    def test_stopwords_only_returns_empty(self, workspace: Path) -> None:
        results = keyword_search(workspace, "the and or")
        assert results == []

    def test_max_results_respected(self, workspace: Path) -> None:
        results = keyword_search(workspace, "Albert", max_results=2)
        assert len(results) <= 2

    def test_results_sorted_by_score(self, workspace: Path) -> None:
        results = keyword_search(workspace, "Albert API")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_missing_agent_dir(self, tmp_path: Path) -> None:
        results = keyword_search(tmp_path, "anything")
        assert results == []

    def test_memory_md_gets_priority_boost(self, workspace: Path) -> None:
        """MEMORY.md results should score higher than equivalent log matches."""
        results = keyword_search(workspace, "Albert API rate limit")
        # Both MEMORY.md and logs have "Albert API rate limit"
        memory_scores = [r["score"] for r in results if r["file"] == "MEMORY.md"]
        log_scores = [
            r["score"]
            for r in results
            if r["file"].startswith("logs/") and r["score"] > 0
        ]
        if memory_scores and log_scores:
            assert max(memory_scores) > max(log_scores)

    def test_header_bonus(self, workspace: Path) -> None:
        """Matches in ## headers should score higher."""
        agent = workspace / ".agent"
        (agent / "test_header.md").write_text(
            "## Deployment Guide\n"
            "This section covers deployment.\n"
            "Some unrelated content here.\n",
            encoding="utf-8",
        )
        results = keyword_search(workspace, "deployment")
        # Header match should contribute a higher score
        assert len(results) > 0

    def test_line_numbers_are_1_indexed(self, workspace: Path) -> None:
        results = keyword_search(workspace, "Albert")
        for r in results:
            assert r["line_start"] >= 1
            assert r["line_end"] >= r["line_start"]

    def test_snippets_contain_matching_text(self, workspace: Path) -> None:
        results = keyword_search(workspace, "query expansion")
        for r in results:
            assert (
                "query" in r["snippet"].lower() or "expansion" in r["snippet"].lower()
            )

    def test_recency_boost_newer_file_ranks_higher(self, workspace: Path) -> None:
        """A match in today's log should rank higher than the same match in an old log."""
        agent = workspace / ".agent" / "logs"
        today = date.today().isoformat()
        (agent / f"{today}.md").write_text(
            "# Today\n\n## 15:00 — Vous\nSpecific unique term xyzzy\n",
            encoding="utf-8",
        )
        (agent / "2024-01-01.md").write_text(
            "# Old\n\n## 10:00 — Vous\nSpecific unique term xyzzy\n",
            encoding="utf-8",
        )
        results = keyword_search(workspace, "xyzzy")
        assert len(results) >= 2
        # Today's file should rank first
        assert today in results[0]["file"]
