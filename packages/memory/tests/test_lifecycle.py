"""Tests for lifecycle hooks — checkpointing, finalisation, git commit."""

import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rag_facile.memory.lifecycle import (
    _extract_topics,
    _format_transcript,
    finalize_session,
    git_commit_session,
    increment_session_count,
    run_checkpoint,
    should_checkpoint,
)
from rag_facile.memory.stores import SemanticStore


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path):
    """Workspace with profile.md for session count tests."""
    agent_dir = tmp_path / ".rag-facile" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "profile.md").write_text(
        "# Profile\n\n## Session Count\n0\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture()
def turns():
    """Sample conversation turns."""
    return [
        {"role": "user", "content": "Qu'est-ce que le chunking ?"},
        {
            "role": "assistant",
            "content": "Le chunking est le processus de découpage des documents.",
        },
        {"role": "user", "content": "Et les embeddings ?"},
        {
            "role": "assistant",
            "content": "Les embeddings sont des représentations vectorielles.",
        },
    ]


# ── should_checkpoint ─────────────────────────────────────────────────────────


class TestShouldCheckpoint:
    def test_false_at_zero(self):
        assert should_checkpoint(0) is False

    def test_true_at_interval(self):
        assert should_checkpoint(8) is True
        assert should_checkpoint(16) is True

    def test_false_between_intervals(self):
        assert should_checkpoint(5) is False
        assert should_checkpoint(7) is False

    def test_custom_interval(self):
        assert should_checkpoint(4, interval=4) is True
        assert should_checkpoint(3, interval=4) is False


# ── run_checkpoint ────────────────────────────────────────────────────────────


class TestRunCheckpoint:
    def test_no_op_on_empty_turns(self, workspace):
        run_checkpoint(workspace, [])
        logs_dir = workspace / ".rag-facile" / "agent" / "logs"
        assert not logs_dir.exists() or not list(logs_dir.glob("*.md"))

    def test_writes_checkpoint_to_log(self, workspace, turns):
        run_checkpoint(workspace, turns)
        from rag_facile.memory.stores import EpisodicLog

        content = EpisodicLog.today_path(workspace).read_text()
        assert "Checkpoint" in content

    def test_uses_summarise_fn_when_provided(self, workspace, turns):
        mock_summarise = MagicMock(return_value="Custom summary here")
        run_checkpoint(workspace, turns, summarise_fn=mock_summarise)
        from rag_facile.memory.stores import EpisodicLog

        content = EpisodicLog.today_path(workspace).read_text()
        assert "Custom summary" in content

    def test_fallback_uses_last_assistant_message(self, workspace, turns):
        run_checkpoint(workspace, turns)
        from rag_facile.memory.stores import EpisodicLog

        content = EpisodicLog.today_path(workspace).read_text()
        assert "vectorielles" in content  # from last assistant message


# ── finalize_session ──────────────────────────────────────────────────────────


class TestFinalizeSession:
    def test_no_op_on_empty_turns(self, workspace):
        finalize_session(workspace, [], datetime.now())
        sessions_dir = workspace / ".rag-facile" / "agent" / "sessions"
        assert not sessions_dir.exists() or not list(sessions_dir.glob("*.md"))

    def test_creates_snapshot(self, workspace, turns):
        with patch("rag_facile.memory.lifecycle.git_commit_session"):
            finalize_session(workspace, turns, datetime(2026, 3, 1, 21, 30))

        sessions_dir = workspace / ".rag-facile" / "agent" / "sessions"
        assert len(list(sessions_dir.glob("*.md"))) == 1

    def test_increments_session_count(self, workspace, turns):
        with patch("rag_facile.memory.lifecycle.git_commit_session"):
            finalize_session(workspace, turns, datetime(2026, 3, 1, 21, 30))

        profile = (workspace / ".rag-facile" / "agent" / "profile.md").read_text()
        assert "## Session Count\n1" in profile

    def test_extracts_facts_when_fn_provided(self, workspace, turns):
        SemanticStore.create(workspace)
        mock_extract = MagicMock(return_value=["User is learning about RAG"])
        with patch("rag_facile.memory.lifecycle.git_commit_session"):
            finalize_session(
                workspace,
                turns,
                datetime(2026, 3, 1, 21, 30),
                extract_facts_fn=mock_extract,
            )

        content = (workspace / ".rag-facile" / "agent" / "memory.md").read_text()
        assert "learning about RAG" in content

    def test_uses_summarise_fn(self, workspace, turns):
        mock_summarise = MagicMock(return_value="Explored chunking concepts")
        with patch("rag_facile.memory.lifecycle.git_commit_session"):
            finalize_session(
                workspace,
                turns,
                datetime(2026, 3, 1, 21, 30),
                summarise_fn=mock_summarise,
            )

        sessions_dir = workspace / ".rag-facile" / "agent" / "sessions"
        snapshot = next(sessions_dir.glob("*.md"))
        assert "chunking" in snapshot.name  # slug from summary

    def test_graceful_on_extract_failure(self, workspace, turns):
        SemanticStore.create(workspace)
        mock_extract = MagicMock(side_effect=ValueError("API error"))
        with patch("rag_facile.memory.lifecycle.git_commit_session"):
            # Should not raise
            finalize_session(
                workspace,
                turns,
                datetime(2026, 3, 1, 21, 30),
                extract_facts_fn=mock_extract,
            )


# ── increment_session_count ───────────────────────────────────────────────────


class TestIncrementSessionCount:
    def test_increments_from_zero(self, workspace):
        assert increment_session_count(workspace) == 1

    def test_updates_file(self, workspace):
        increment_session_count(workspace)
        content = (workspace / ".rag-facile" / "agent" / "profile.md").read_text()
        assert "## Session Count\n1" in content

    def test_increments_twice(self, workspace):
        increment_session_count(workspace)
        assert increment_session_count(workspace) == 2

    def test_returns_one_when_no_profile(self, tmp_path):
        assert increment_session_count(tmp_path) == 1


# ── git_commit_session ────────────────────────────────────────────────────────


class TestGitCommitSession:
    def test_silent_when_git_not_found(self, workspace):
        with patch(
            "rag_facile.memory.lifecycle.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            git_commit_session(workspace)  # should not raise

    def test_skips_silently_when_gitignored(self, workspace):
        check_ignore = MagicMock(returncode=0)  # 0 = ignored
        with patch(
            "rag_facile.memory.lifecycle.subprocess.run",
            return_value=check_ignore,
        ) as mock_run:
            git_commit_session(workspace)

        assert mock_run.call_count == 1  # only check-ignore

    def test_skips_when_nothing_staged(self, workspace):
        check_ignore = MagicMock(returncode=1)
        add_result = MagicMock(returncode=0)
        diff_result = MagicMock(returncode=0)  # 0 = nothing staged

        with patch(
            "rag_facile.memory.lifecycle.subprocess.run",
            side_effect=[check_ignore, add_result, diff_result],
        ) as mock_run:
            git_commit_session(workspace)

        assert mock_run.call_count == 3  # check-ignore + add + diff, no commit

    def test_warns_on_git_failure(self, workspace):
        err = subprocess.CalledProcessError(1, "git", stderr=b"error")
        with patch(
            "rag_facile.memory.lifecycle.subprocess.run",
            side_effect=err,
        ):
            git_commit_session(workspace)  # should not raise


# ── Helpers ───────────────────────────────────────────────────────────────────


class TestFormatTranscript:
    def test_formats_turns(self):
        turns = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        result = _format_transcript(turns)
        assert "Vous: Hello" in result
        assert "Assistant: Hi!" in result


class TestExtractTopics:
    def test_extracts_keywords(self):
        turns = [
            {"role": "user", "content": "What is chunking and embedding?"},
            {"role": "user", "content": "Tell me about chunking strategies"},
        ]
        topics = _extract_topics(turns)
        assert "chunking" in topics

    def test_excludes_stopwords(self):
        turns = [
            {"role": "user", "content": "the quick brown fox jumps over the lazy dog"}
        ]
        topics = _extract_topics(turns)
        assert "the" not in topics

    def test_max_topics(self):
        turns = [
            {
                "role": "user",
                "content": "alpha bravo charlie delta echo foxtrot golf hotel",
            }
        ]
        topics = _extract_topics(turns, max_topics=3)
        assert len(topics) <= 3

    def test_ignores_assistant_turns(self):
        turns = [
            {"role": "assistant", "content": "uniqueword12345"},
            {"role": "user", "content": "Something else here"},
        ]
        topics = _extract_topics(turns)
        assert "uniqueword12345" not in topics
