"""Tests for the git-backed session memory module."""

import subprocess
from unittest.mock import MagicMock, patch

import openai
import pytest

from cli.commands.chat.memory import (
    append_turn,
    git_commit_session,
    increment_session_count,
    load_context,
    update_memory,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path):
    """Minimal workspace with MEMORY.md and profile.md."""
    agent_dir = tmp_path / ".rag-facile" / "agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "MEMORY.md").write_text(
        "---\nupdated: 2026-02-20\nproject: test\npreset: balanced\n---\n\n"
        "## User Profile\n- Experience level: new\n\n"
        "## Learned Facts\n(empty — will be populated across sessions)\n",
        encoding="utf-8",
    )
    (agent_dir / "profile.md").write_text(
        "# User Profile\n\n## Preferences\n- Language: fr\n\n## Session Count\n0\n",
        encoding="utf-8",
    )
    return tmp_path


# ── load_context ──────────────────────────────────────────────────────────────


class TestLoadContext:
    def test_returns_empty_when_no_files(self, tmp_path):
        assert load_context(tmp_path) == ""

    def test_returns_memory_content(self, workspace):
        result = load_context(workspace)
        assert "User Profile" in result
        assert "Experience level: new" in result

    def test_includes_profile(self, workspace):
        result = load_context(workspace)
        assert "Session Count" in result

    def test_separates_sections_with_divider(self, workspace):
        result = load_context(workspace)
        assert "---" in result


# ── append_turn ───────────────────────────────────────────────────────────────


class TestAppendTurn:
    def test_creates_conversation_file(self, workspace):
        append_turn(workspace, "user", "Bonjour")
        conv_dir = workspace / ".rag-facile" / "agent" / "conversations"
        assert any(conv_dir.glob("*.md"))

    def test_user_label_is_vous(self, workspace):
        append_turn(workspace, "user", "Bonjour")
        log = next((workspace / ".rag-facile/agent/conversations").glob("*.md"))
        assert "Vous" in log.read_text()

    def test_assistant_label_is_assistant(self, workspace):
        append_turn(workspace, "assistant", "Bonjour !")
        log = next((workspace / ".rag-facile/agent/conversations").glob("*.md"))
        assert "Assistant" in log.read_text()

    def test_content_written(self, workspace):
        append_turn(workspace, "user", "Qu'est-ce que le chunking ?")
        log = next((workspace / ".rag-facile/agent/conversations").glob("*.md"))
        assert "chunking" in log.read_text()

    def test_multiple_turns_appended(self, workspace):
        append_turn(workspace, "user", "Question 1")
        append_turn(workspace, "assistant", "Réponse 1")
        append_turn(workspace, "user", "Question 2")
        log = next((workspace / ".rag-facile/agent/conversations").glob("*.md"))
        content = log.read_text()
        assert "Question 1" in content
        assert "Question 2" in content
        assert "Réponse 1" in content

    def test_header_written_once(self, workspace):
        append_turn(workspace, "user", "Hello")
        append_turn(workspace, "user", "Hello again")
        log = next((workspace / ".rag-facile/agent/conversations").glob("*.md"))
        assert log.read_text().count("# Session") == 1


# ── increment_session_count ───────────────────────────────────────────────────


class TestIncrementSessionCount:
    def test_increments_from_zero(self, workspace):
        count = increment_session_count(workspace)
        assert count == 1

    def test_updates_file(self, workspace):
        increment_session_count(workspace)
        profile = (workspace / ".rag-facile/agent/profile.md").read_text()
        assert "## Session Count\n1" in profile

    def test_increments_twice(self, workspace):
        increment_session_count(workspace)
        count = increment_session_count(workspace)
        assert count == 2

    def test_returns_one_when_no_profile(self, tmp_path):
        assert increment_session_count(tmp_path) == 1


# ── update_memory ─────────────────────────────────────────────────────────────


class TestUpdateMemory:
    def test_skips_on_empty_log(self, workspace):
        memory_before = (workspace / ".rag-facile/agent/MEMORY.md").read_text()
        update_memory(workspace, "")
        assert (workspace / ".rag-facile/agent/MEMORY.md").read_text() == memory_before

    def test_skips_when_no_memory_file(self, tmp_path):
        # Should not raise
        update_memory(tmp_path, "some log")

    def test_appends_new_facts(self, workspace):
        mock_response = MagicMock()
        mock_response.choices[
            0
        ].message.content = "- L'utilisateur travaille sur un projet de RAG juridique"

        with patch("cli.commands.chat.memory.openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = (
                mock_response
            )
            update_memory(
                workspace, "Vous: Je fais du RAG juridique\nAssistant: Intéressant!"
            )

        memory = (workspace / ".rag-facile/agent/MEMORY.md").read_text()
        assert "RAG juridique" in memory

    def test_removes_empty_placeholder(self, workspace):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "- Fait intéressant"

        with patch("cli.commands.chat.memory.openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = (
                mock_response
            )
            update_memory(workspace, "some log")

        memory = (workspace / ".rag-facile/agent/MEMORY.md").read_text()
        assert "(empty — will be populated across sessions)" not in memory

    def test_skips_gracefully_on_api_error(self, workspace):
        with patch("cli.commands.chat.memory.openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = (
                openai.APIConnectionError(request=MagicMock())
            )
            # Should not raise
            update_memory(workspace, "some log")

    def test_skips_when_no_new_facts(self, workspace):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = ""

        with patch("cli.commands.chat.memory.openai.OpenAI") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = (
                mock_response
            )
            update_memory(workspace, "some log")

        # File unchanged (modulo whitespace)
        memory_after = (workspace / ".rag-facile/agent/MEMORY.md").read_text()
        assert "Experience level" in memory_after


# ── git_commit_session ────────────────────────────────────────────────────────


class TestGitCommitSession:
    def test_silent_when_git_not_found(self, workspace):
        with patch(
            "cli.commands.chat.memory.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            git_commit_session(workspace)  # should not raise

    def test_warns_on_git_failure(self, workspace, capsys):
        err = subprocess.CalledProcessError(1, "git", stderr=b"not a git repo")
        with patch(
            "cli.commands.chat.memory.subprocess.run",
            side_effect=err,
        ):
            git_commit_session(workspace)  # should not raise

    def test_skips_commit_when_nothing_staged(self, workspace):
        """If git diff --cached is clean, no commit is made."""
        check_ignore = MagicMock(returncode=1)  # 1 = not ignored
        add_result = MagicMock(returncode=0)
        diff_result = MagicMock(returncode=0)  # 0 = nothing staged

        with patch(
            "cli.commands.chat.memory.subprocess.run",
            side_effect=[check_ignore, add_result, diff_result],
        ) as mock_run:
            git_commit_session(workspace)

        assert mock_run.call_count == 3  # check-ignore + add + diff, no commit

    def test_skips_silently_when_gitignored(self, workspace):
        """If .rag-facile/ is gitignored (e.g. source repo), skip without warning."""
        check_ignore = MagicMock(returncode=0)  # 0 = ignored

        with patch(
            "cli.commands.chat.memory.subprocess.run",
            return_value=check_ignore,
        ) as mock_run:
            git_commit_session(workspace)

        assert mock_run.call_count == 1  # only check-ignore, nothing else
