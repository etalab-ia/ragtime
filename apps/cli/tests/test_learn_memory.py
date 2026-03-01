"""Tests for the user profile context module."""

import pytest

from cli.commands.learn.memory import (
    increment_session_count,
    load_context,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path):
    """Minimal workspace with profile.md."""
    agent_dir = tmp_path / ".rag-facile" / "agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "profile.md").write_text(
        "# User Profile\n\n## Preferences\n- Language: fr\n- Experience level: New to RAG\n\n## Session Count\n0\n",
        encoding="utf-8",
    )
    return tmp_path


# ── load_context ──────────────────────────────────────────────────────────────


class TestLoadContext:
    def test_returns_empty_when_no_files(self, tmp_path):
        assert load_context(tmp_path) == ""

    def test_returns_profile_content(self, workspace):
        result = load_context(workspace)
        assert "User Profile" in result

    def test_includes_language_preference(self, workspace):
        result = load_context(workspace)
        assert "Language: fr" in result

    def test_includes_session_count(self, workspace):
        result = load_context(workspace)
        assert "Session Count" in result


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
