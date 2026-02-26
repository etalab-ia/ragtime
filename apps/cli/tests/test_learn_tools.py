"""Tests for the chat agent tools (get_agents_md, get_recent_git_activity, get_docs)."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from cli.commands.learn.tools import (
    get_agents_md,
    get_docs,
    get_recent_git_activity,
    set_workspace_root,
)


@pytest.fixture(autouse=True)
def reset_workspace():
    """Reset the module-level workspace root before and after each test."""
    set_workspace_root(None)
    yield
    set_workspace_root(None)


@pytest.fixture()
def workspace(tmp_path):
    """Workspace with ragfacile.toml, AGENTS.md, and a git repo."""
    (tmp_path / "ragfacile.toml").write_text(
        "[meta]\npreset = 'balanced'\n", encoding="utf-8"
    )
    (tmp_path / "AGENTS.md").write_text(
        "# Project Architecture\n\nThis is a rag-facile workspace.\n", encoding="utf-8"
    )
    set_workspace_root(tmp_path)
    return tmp_path


# ── get_agents_md ─────────────────────────────────────────────────────────────


class TestGetAgentsMd:
    def test_returns_hint_when_no_workspace(self):
        result = get_agents_md()
        assert "No workspace detected" in result

    def test_returns_agents_md_content(self, workspace):
        result = get_agents_md()
        assert "Project Architecture" in result
        assert "rag-facile workspace" in result

    def test_returns_hint_when_no_agents_md(self, tmp_path):
        set_workspace_root(tmp_path)
        result = get_agents_md()
        assert "No AGENTS.md found" in result


# ── get_recent_git_activity ───────────────────────────────────────────────────


class TestGetRecentGitActivity:
    def test_returns_hint_when_no_workspace(self):
        result = get_recent_git_activity()
        assert "No workspace detected" in result

    def test_returns_log_output(self, workspace):
        mock_result = MagicMock()
        mock_result.stdout = "abc1234 feat: initial commit\n"
        with patch(
            "cli.commands.learn.tools.subprocess.run", return_value=mock_result
        ) as mock_run:
            result = get_recent_git_activity()

        mock_run.assert_called_once_with(
            ["git", "log", "--oneline", "--decorate", "--no-merges", "-15"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result == "abc1234 feat: initial commit"

    def test_returns_no_commits_message_on_empty_log(self, workspace):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("cli.commands.learn.tools.subprocess.run", return_value=mock_result):
            result = get_recent_git_activity()
        assert "No commits found" in result

    def test_returns_hint_when_git_not_installed(self, workspace):
        with patch(
            "cli.commands.learn.tools.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = get_recent_git_activity()
        assert "git is not installed" in result

    def test_returns_error_on_git_failure(self, workspace):
        with patch(
            "cli.commands.learn.tools.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                128, "git", stderr="not a git repo"
            ),
        ):
            result = get_recent_git_activity()
        assert result == "git log failed: not a git repo"


# ── get_docs ──────────────────────────────────────────────────────────────────


class TestGetDocs:
    def _make_docs_dir(self, tmp_path):
        """Create a minimal docs structure mirroring the real docs/."""
        guides = tmp_path / "docs" / "guides"
        reference = tmp_path / "docs" / "reference"
        guides.mkdir(parents=True)
        reference.mkdir(parents=True)
        (guides / "how-rag-works.md").write_text(
            "# How RAG Works\nContent here.", encoding="utf-8"
        )
        (reference / "ragfacile-toml.md").write_text(
            "# Configuration\nPreset options.", encoding="utf-8"
        )
        return tmp_path / "docs"

    def test_returns_index_on_empty_topic(self, tmp_path):
        docs_dir = self._make_docs_dir(tmp_path)
        with patch("cli.commands.learn.tools._get_docs_dir", return_value=docs_dir):
            result = get_docs("")
        assert "Available rag-facile documentation" in result
        assert "rag" in result

    def test_returns_doc_content_on_match(self, tmp_path):
        docs_dir = self._make_docs_dir(tmp_path)
        with patch("cli.commands.learn.tools._get_docs_dir", return_value=docs_dir):
            result = get_docs("rag")
        assert "How RAG Works" in result

    def test_partial_topic_match(self, tmp_path):
        docs_dir = self._make_docs_dir(tmp_path)
        with patch("cli.commands.learn.tools._get_docs_dir", return_value=docs_dir):
            result = get_docs("preset configuration")
        assert "Configuration" in result

    def test_returns_hint_on_unknown_topic(self, tmp_path):
        docs_dir = self._make_docs_dir(tmp_path)
        with patch("cli.commands.learn.tools._get_docs_dir", return_value=docs_dir):
            result = get_docs("foobar")
        assert "No documentation found" in result
        assert "Available topics" in result

    def test_returns_hint_when_docs_not_found(self):
        with patch("cli.commands.learn.tools._get_docs_dir", return_value=None):
            result = get_docs("rag")
        assert "not found" in result.lower()
